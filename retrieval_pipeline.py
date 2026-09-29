"""
CloudDesk AI Support Engineer — Retrieval & Inference Pipeline (corrected)
==========================================================================
Connects to the pre-indexed vector DB (Pinecone, falling back to local
ChromaDB), retrieves context, formats citations, scores confidence and
generates grounded answers via the HuggingFace InferenceClient.

All secrets are read from a local .env file (see .env.example). Never paste
keys into this file.
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from sentence_transformers import SentenceTransformer
import chromadb

try:
    from pinecone import Pinecone
except ImportError:
    Pinecone = None

# -------------------------------------------------------------
# 1. Configuration & prompts
# -------------------------------------------------------------
RETRIEVE_K = 5   # candidates pulled from the vector DB (needed for Hit@5)
CONTEXT_K = 3    # top chunks passed to the LLM and used for confidence
CHROMA_COLLECTION = "clouddesk_support_kb"

SYSTEM_PROMPT = """You are the CloudDesk AI Support Engineer.
Answer customer support questions accurately based ONLY on the provided context.
Provide a clear step-by-step resolution and cite source documents.
If the answer is not present in the context or confidence is low, state that clearly and suggest contacting Tier-2 Support."""

FALLBACK_MESSAGE = (
    "[ESCALATED] Answer Confidence Below Threshold (< 60%) — Auto-Escalated to Human Support\n\n"
    "This query has been escalated to CloudDesk Support Engineering for assistance."
)


def load_config() -> Dict[str, Any]:
    """Read settings from environment variables / .env (no secrets in code)."""
    load_dotenv()
    cfg = {
        "hf_token": os.getenv("HF_TOKEN"),
        "hf_model": os.getenv("HF_MODEL", "deepseek-ai/DeepSeek-V4-Pro:novita"),
        "pinecone_api_key": os.getenv("PINECONE_API_KEY"),
        "pinecone_index": os.getenv("PINECONE_INDEX_NAME", "clouddesk-support-rag"),
        "embed_model": os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        "vector_db_dir": os.getenv("VECTOR_DB_DIR", "vector_db"),
        "confidence_threshold": float(os.getenv("CONFIDENCE_THRESHOLD", "0.60")),
        "retrieve_k": int(os.getenv("RETRIEVE_K", RETRIEVE_K)),
        "context_k": int(os.getenv("CONTEXT_K", CONTEXT_K)),
    }
    if not cfg["hf_token"]:
        print("[!] HF_TOKEN not set — answers will use the extractive fallback (no LLM).")
    return cfg


# -------------------------------------------------------------
# 2. Vector store connection & retrieval
# -------------------------------------------------------------
def get_vector_store(cfg: Dict[str, Any]) -> Dict[str, Any]:
    embedder = SentenceTransformer(cfg["embed_model"])

    if cfg.get("pinecone_api_key") and Pinecone:
        try:
            pc = Pinecone(api_key=cfg["pinecone_api_key"])
            index = pc.Index(cfg["pinecone_index"])
            n_vectors = getattr(index.describe_index_stats(), "total_vector_count", 0)
            if n_vectors > 0:
                print(f"[*] Using Pinecone index '{cfg['pinecone_index']}' ({n_vectors} vectors)")
                return {"type": "pinecone", "handle": index, "embedder": embedder, "space": "cosine"}
            print("[!] Pinecone index is empty — falling back to local Chroma.")
        except Exception as e:
            print(f"[!] Pinecone connection failed: {e} — falling back to local Chroma.")

    # The indexing notebook persists Chroma under <VECTOR_DB_DIR>/chroma
    path = os.path.join(cfg["vector_db_dir"], "chroma")
    client = chromadb.PersistentClient(path=path)
    try:
        coll = client.get_collection(CHROMA_COLLECTION)   # fail loudly, don't create an empty one
    except Exception as e:
        raise RuntimeError(
            f"Chroma collection '{CHROMA_COLLECTION}' not found at '{path}'. "
            f"Run 01_data_ingestion_and_indexing.ipynb first."
        ) from e
    if coll.count() == 0:
        raise RuntimeError(f"Chroma collection at '{path}' is empty — re-run the indexing notebook.")

    space = (coll.metadata or {}).get("hnsw:space", "l2")  # Chroma's default metric is squared L2
    print(f"[*] Using local Chroma at '{path}' ({coll.count()} vectors, space={space})")
    return {"type": "chroma", "handle": coll, "embedder": embedder, "space": space}


def _to_similarity(distance: float, space: str) -> float:
    """Convert a Chroma distance into a 0-1 similarity (embeddings are unit-normalised)."""
    if space == "l2":
        sim = 1.0 - distance / 2.0      # squared L2 on unit vectors = 2 * (1 - cosine)
    else:                               # 'cosine' or 'ip'
        sim = 1.0 - distance
    return max(0.0, min(1.0, sim))


def retrieve_docs(vstore: Dict[str, Any], query: str, k: int = RETRIEVE_K,
                  exclude_chunk_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return the top-k chunks. `exclude_chunk_id` lets evaluation hide a ticket's own chunk."""
    q_emb = vstore["embedder"].encode([query], normalize_embeddings=True)[0].tolist()
    docs: List[Dict[str, Any]] = []

    if vstore["type"] == "pinecone":
        kwargs: Dict[str, Any] = dict(vector=q_emb, top_k=k, include_metadata=True)
        if exclude_chunk_id:
            kwargs["filter"] = {"chunk_id": {"$ne": exclude_chunk_id}}
        res = vstore["handle"].query(**kwargs)
        for m in res.matches:
            meta = m.metadata or {}
            docs.append({
                "text": meta.get("text") or meta.get("page_content", ""),
                "title": meta.get("title", "CloudDesk Doc"),
                "source_type": meta.get("source_type", "doc"),
                "chunk_id": meta.get("chunk_id", m.id),
                "score": round(max(0.0, min(1.0, float(m.score))), 4),
            })
    else:
        kwargs = dict(query_embeddings=[q_emb], n_results=k,
                      include=["documents", "metadatas", "distances"])
        if exclude_chunk_id:
            kwargs["where"] = {"chunk_id": {"$ne": exclude_chunk_id}}
        res = vstore["handle"].query(**kwargs)
        for text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            docs.append({
                "text": text,
                "title": meta.get("title", "CloudDesk Doc"),
                "source_type": meta.get("source_type", "doc"),
                "chunk_id": meta.get("chunk_id", ""),
                "score": round(_to_similarity(float(dist), vstore["space"]), 4),
            })
    return docs


# -------------------------------------------------------------
# 3. Formatting & confidence scoring
# -------------------------------------------------------------
def format_docs(docs: List[Dict[str, Any]]) -> Tuple[str, str]:
    blocks, cites = [], []
    for d in docs:
        cites.append(f"- **[{d['title']}]** (`{d['source_type']}`) — Similarity: {d['score'] * 100:.0f}%")
        blocks.append(f"[{d['title']} ({d['source_type']})]\n{d['text']}")
    return "\n\n---\n\n".join(blocks), "\n".join(cites)


def compute_confidence(docs: List[Dict[str, Any]]) -> float:
    """0.6 * top score + 0.4 * mean score. NOTE: MiniLM cosine scores for a good match are
    typically 0.4-0.7, so calibrate CONFIDENCE_THRESHOLD against the eval set (see evaluate_benchmark)."""
    if not docs:
        return 0.0
    top_score = docs[0]["score"]
    avg_score = sum(d["score"] for d in docs) / float(len(docs))
    return round(0.6 * top_score + 0.4 * avg_score, 4)


# -------------------------------------------------------------
# 4. LLM call & RAG execution
# -------------------------------------------------------------
def call_hf_chat(client: InferenceClient, model_id: str, system: str, user_content: str) -> str:
    completion = client.chat.completions.create(
        model=model_id,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
        max_tokens=512,
    )
    return completion.choices[0].message.content


def run_rag_pipeline(cfg: Dict[str, Any], vstore: Dict[str, Any], client: Optional[InferenceClient],
                     query: str, exclude_chunk_id: Optional[str] = None,
                     generate: bool = True) -> Dict[str, Any]:
    candidates = retrieve_docs(vstore, query, k=cfg["retrieve_k"], exclude_chunk_id=exclude_chunk_id)
    docs = candidates[: cfg["context_k"]]            # only the best chunks go to the LLM
    context, cites = format_docs(docs)
    confidence = compute_confidence(docs)
    requires_escalation = confidence < cfg["confidence_threshold"]

    answer = ""
    if requires_escalation:
        answer = FALLBACK_MESSAGE                    # don't spend an LLM call on low-confidence queries
    elif generate:
        if client and cfg.get("hf_token"):
            user_prompt = f"Customer Question: {query}\n\nContext:\n{context}\n\nAnswer:"
            try:
                answer = call_hf_chat(client, cfg["hf_model"], SYSTEM_PROMPT, user_prompt)
            except Exception as e:
                print(f"[!] HuggingFace API error: {e}")
        if not answer and docs:                      # extractive fallback
            top_doc = docs[0]
            clean_text = top_doc["text"].strip().replace("\n", "\n> ")
            answer = (
                f"### Resolution Guide for CloudDesk Customer Support\n"
                f"**Confidence:** {confidence * 100:.0f}% | **Source:** [{top_doc['title']}]\n\n"
                f"Based on CloudDesk documentation:\n"
                f"> {clean_text[:500]}\n\n"
                f"**Verified Sources:**\n{cites}"
            )

    return {
        "query": query,
        "answer": answer,
        "confidence": confidence,
        "confidence_pct": f"{confidence * 100:.0f}%",
        "requires_escalation": requires_escalation,
        "citations": cites,
        "docs": docs,
        "candidates": candidates,
    }


# -------------------------------------------------------------
# 5. Evaluation benchmark
# -------------------------------------------------------------
HARD_TICKETS = ["tkt_10034", "tkt_10051", "tkt_10121"]   # should escalate / score lower
EASY_TICKETS = ["tkt_10052", "tkt_10061"]                # should score confidently high


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(s).lower()).strip()


def _title_match(ref_title: str, doc_title: str) -> bool:
    r, t = _norm(ref_title), _norm(doc_title)
    return bool(r) and bool(t) and (r in t or t in r)


def evaluate_benchmark(cfg: Dict[str, Any], vstore: Dict[str, Any], client: Optional[InferenceClient] = None,
                       csv_path: Optional[str] = None, out_csv: str = "eval_results.csv") -> Dict[str, Any]:
    if csv_path is None:
        csv_path = os.path.join("clouddesk_dataset", "support_tickets", "previous_support_tickets.csv")
    if not os.path.exists(csv_path):
        print(f"[!] Test CSV path '{csv_path}' not found.")
        return {}

    df = pd.read_csv(csv_path)
    print(f"[*] Running RAG evaluation across {len(df)} historical tickets "
          f"(retrieve_k={cfg['retrieve_k']}, context_k={cfg['context_k']}, "
          f"threshold={cfg['confidence_threshold']})...")

    records, skipped = [], 0
    for idx, r in df.iterrows():
        tkt_id = str(r.get("ticket_id", f"tkt_{idx}"))
        query = str(r.get("customer_question", ""))
        ref_title = str(r.get("source_title_reference", "")).strip()
        if not ref_title or ref_title.lower() == "nan":
            skipped += 1
            continue

        # Hide the ticket's own indexed chunk — otherwise the answer is in the index (leakage).
        res = run_rag_pipeline(cfg, vstore, client, query,
                               exclude_chunk_id=f"ticket_{tkt_id}", generate=False)
        first_rank = next((rank for rank, d in enumerate(res["candidates"], 1)
                           if _title_match(ref_title, d["title"])), None)
        records.append({
            "ticket_id": tkt_id,
            "question": query,
            "ref_title": ref_title,
            "top_retrieved": res["candidates"][0]["title"] if res["candidates"] else "None",
            "first_match_rank": first_rank,
            "confidence": res["confidence"],
            "escalated": res["requires_escalation"],
            "hit_at_1": first_rank == 1,
            "hit_at_3": first_rank is not None and first_rank <= 3,
            "hit_at_5": first_rank is not None and first_rank <= 5,
        })

    rec = pd.DataFrame(records)
    total = len(rec)
    if total == 0:
        print("[!] No evaluable tickets.")
        return {}

    metrics = {
        "total_tickets": total,
        "skipped_no_reference": skipped,
        "hit_rate_at_1_pct": f"{rec['hit_at_1'].mean() * 100:.2f}%",
        "hit_rate_at_3_pct": f"{rec['hit_at_3'].mean() * 100:.2f}%",
        "hit_rate_at_5_pct": f"{rec['hit_at_5'].mean() * 100:.2f}%",
        "mean_confidence": round(float(rec["confidence"].mean()), 4),
        "total_escalations": int(rec["escalated"].sum()),
        "escalation_rate_pct": f"{rec['escalated'].mean() * 100:.2f}%",
        "records": records,
    }

    print("\n========================================================")
    print("          CLOUDDESK RAG BENCHMARK EVALUATION RESULTS     ")
    print("========================================================")
    print(f" Tickets Tested       : {metrics['total_tickets']} (skipped {skipped} without a reference)")
    print(f" Hit Rate @ 1 / 3 / 5 : {metrics['hit_rate_at_1_pct']} / "
          f"{metrics['hit_rate_at_3_pct']} / {metrics['hit_rate_at_5_pct']}")
    print(f" Mean Confidence      : {metrics['mean_confidence']}")
    print(f" Escalations          : {metrics['total_escalations']} ({metrics['escalation_rate_pct']})")
    for label, ids in (("Hard", HARD_TICKETS), ("Easy", EASY_TICKETS)):
        sub = rec[rec["ticket_id"].isin(ids)]
        for _, s in sub.iterrows():
            print(f" {label:<5} {s['ticket_id']}: conf={s['confidence']:.2f} escalated={s['escalated']} "
                  f"hit@3={s['hit_at_3']}")
    print("========================================================\n")

    rec.to_csv(out_csv, index=False)
    print(f"[*] Per-ticket results saved to {out_csv}")
    return metrics


# -------------------------------------------------------------
# Entry point
# -------------------------------------------------------------
if __name__ == "__main__":
    cfg = load_config()
    print("[*] Connecting to vector store...")
    vstore = get_vector_store(cfg)
    client = InferenceClient(api_key=cfg["hf_token"]) if cfg.get("hf_token") else None

    sample_query = "My SAML login stopped working after adding a new domain"
    print(f"\n[*] Testing sample query: '{sample_query}'\n")
    res = run_rag_pipeline(cfg, vstore, client, sample_query)

    print(f"Confidence : {res['confidence_pct']}")
    print(f"Escalated  : {res['requires_escalation']}")
    print(f"Sources    :\n{res['citations']}")
    print(f"\nAnswer:\n{res['answer']}")

    # Uncomment to run the full 43-ticket benchmark:
    evaluate_benchmark(cfg, vstore, client)
