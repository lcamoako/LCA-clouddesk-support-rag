# CloudDesk AI Support Assistant (RAG System)

**Role:** Consultant Intern, Amdari  
**Focus:** Generative AI, Retrieval-Augmented Generation (RAG), Support Automation  

---

## 📌 Project Overview
As a Consultant Intern with Amdari, I developed the **CloudDesk AI Support Assistant** to address high support ticket volumes in enterprise software environments. 

The primary business objective was to build an intelligent, context-aware Tier-1 resolution assistant capable of automatically answering technical customer queries (covering API documentation, SAML/SSO setups, webhooks, and billing). The system uses Retrieval-Augmented Generation (RAG) to ensure responses are grounded in verified documentation, with built-in confidence scoring to automatically escalate ambiguous or out-of-scope issues to human engineers.

---

## 🛠️ Tech Stack & Tools Used
* **Python**: Core logic and application workflow.
* **Pinecone**: Hosted vector database used for semantic search and fast vector retrieval.
* **Hugging Face Hub**: Inference endpoints and embedding model hosting.
* **Sentence-Transformers**: Text embedding generation for query-to-document matching.
* **Gradio**: Interactive web-based user interface and diagnostics view.
* **Git & GitHub**: Version control and project repository.

---

## 🚀 Key Implementations & What I Did
1. **Document Ingestion & Indexing:** Processed technical documentation, engineering runbooks, and historical support tickets into a Pinecone vector index.
2. **Retrieval Pipeline Design:** Implemented semantic similarity matching to locate relevant reference articles in real time when a user inputs a support query.
3. **Confidence Scoring & Safe Routing:** Configured a confidence threshold (`CONFIDENCE_THRESHOLD = 0.48`). Queries with high match scores return automated resolution guides, while low-confidence queries route directly to human support escalation.
4. **Interactive Dashboard:** Built a clean Gradio UI to test queries live, inspect retrieved context chunks, and verify system confidence metrics.

---

## 💡 Learning Journey & AI Collaboration
As an early-career technologist still actively growing my coding proficiency, this project was developed using an **AI-assisted engineering methodology**. 

Working alongside AI pair-programming tools allowed me to:
- Translate business requirements into functional Python scripts.
- Work through version control with Git and troubleshoot cloud infrastructure.
- Rapidly learn core concepts in modern RAG systems, such as vector databases, embeddings, and confidence thresholds.

---

## 🏃 Local Setup & Run

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/lcamoako/LCA-clouddesk-support-rag.git](https://github.com/lcamoako/LCA-clouddesk-support-rag.git)
   cd LCA-clouddesk-support-rag
