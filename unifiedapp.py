import os
import gradio as gr
from huggingface_hub import InferenceClient
from retrieval_pipeline import get_vector_store, load_config, run_rag_pipeline

# 1. Initialize configuration, vector store, and Hugging Face client once at startup
print("[*] Initializing CloudDesk RAG pipeline...")
cfg = load_config()
vstore = get_vector_store(cfg)

client = None
if cfg.get("hf_token"):
    client = InferenceClient(token=cfg["hf_token"])
print("[*] Ready for queries.")


def answer_ticket(user_query: str):
    if not user_query.strip():
        return (
            "Awaiting query...",
            "N/A",
            "N/A",
            "No sources consulted.",
        )

    # Single call to the RAG pipeline — avoids double-querying Pinecone
    result = run_rag_pipeline(
        cfg=cfg,
        vstore=vstore,
        client=client,
        query=user_query,
        generate=True,
    )

    answer = result.get("answer", "No answer generated.")
    conf_pct = result.get("confidence_pct", "0%")

    if result.get("requires_escalation"):
        escalation_status = "⚠️ ESCALATED (Passed to Human Agent)"
    else:
        escalation_status = "✅ RESOLVED (Handled by AI Support Assistant)"

    citations = result.get("citations", "None cited.")
    return answer, conf_pct, escalation_status, citations


# 2. UI Theme Definition
cloud_theme = gr.themes.Base(
    primary_hue="pink",
    secondary_hue="cyan",
    neutral_hue="slate",
)

with gr.Blocks(title="CloudDesk AI Support Engineer") as demo:
    # Logo & Gradient Header
    gr.Image(
        "logo.PNG",
        width=350,
        show_label=False,
        interactive=False,
        buttons=[],
    )

    gr.HTML(
        """
        <div style="
            background: linear-gradient(135deg, #24245c, #4b4bb8);
            padding: 12px;
            border-radius: 10px;
            text-align: center;
            color: white;
            margin-bottom: 12px;
        ">
            <h1 style="margin-bottom: 6px; font-size: 28px;">
                ☁️ CloudDesk AI Support Engineer
            </h1>
            <p style="font-size: 15px; opacity: 0.9; margin: 0;">
                Customer Support Retrieval-Augmented Generation (RAG) Copilot
            </p>
        </div>
        """
    )

    with gr.Row():
        # Left Column: User Input & Controls
        with gr.Column(scale=1):
            gr.HTML(
                """
                <div style="
                    background: #e7e7ff;
                    color: #4b4bb8;
                    padding: 4px 10px;
                    border-radius: 8px;
                    font-weight: bold;
                    display: inline-block;
                    margin-bottom: 4px;
                ">
                    Enter Customer Query...
                </div>
                """
            )
            query_box = gr.Textbox(
                show_label=False,
                lines=4,
                placeholder="e.g. My SAML login stopped working after adding a new domain",
            )

            with gr.Row():
                submit_btn = gr.Button("🚀 Submit Query", variant="primary")
                clear_btn = gr.Button("🧹 Clear")

            gr.Examples(
                examples=[
                    ["My SAML login stopped working after adding a new domain"],
                    ["How do I configure automatic user deprovisioning via SCIM with Azure AD?"],
                    ["Can I enforce SSO for a specific subdomain without requiring it for the root domain?"],
                    ["How do I reset my CloudDesk billing credit card and download last month's VAT invoice?"],
                    ["What is the best chocolate chip cookie recipe for a team offsite?"],
                ],
                inputs=query_box,
                label="Try an example query...",
            )

        # Right Column: Generated Answer & Diagnostic Badges
        with gr.Column(scale=1):
            with gr.Row():
                conf_display = gr.Textbox(
                    label="Retrieval Confidence", interactive=False
                )
                status_display = gr.Textbox(
                    label="Routing Decision", interactive=False
                )

            gr.HTML(
                """
                <div style="
                    background: #e7e7ff;
                    color: #4b4bb8;
                    padding: 4px 10px;
                    border-radius: 8px;
                    font-weight: bold;
                    display: inline-block;
                    margin-bottom: 4px;
                ">
                    Generated Resolution Plan
                </div>
                """
            )
            answer_display = gr.Markdown(value="*Awaiting customer query...*")

            with gr.Accordion("📌 Retrieved Evidence & Citations", open=True):
                sources_display = gr.Markdown()

    # Event Handlers
    submit_btn.click(
        fn=answer_ticket,
        inputs=[query_box],
        outputs=[answer_display, conf_display, status_display, sources_display],
    )

    clear_btn.click(
        fn=lambda: ("", "*Awaiting customer query...*", "", "", ""),
        inputs=[],
        outputs=[query_box, answer_display, conf_display, status_display, sources_display],
    )

# 3. Dynamic Port Configuration for Local + Cloud Deployment
PORT = int(os.environ.get("PORT", 7860))

if __name__ == "__main__":
    demo.launch(
        share=True,
        allowed_paths=["./"],
        theme=cloud_theme,
        server_name="0.0.0.0",
        server_port=PORT,
    )
