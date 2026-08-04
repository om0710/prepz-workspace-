import os
import gradio as gr
from app import app as fastapi_app

# Mount FastAPI app onto Gradio Blocks interface so Gradio SDK launcher runs seamlessly
demo = gr.mount_gradio_app(fastapi_app, gr.Blocks(title="Prepz AI Workspace"), path="/")
app = demo

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"[HF SPACE] Launching Gradio mounted Prepz AI server on port {port}...")
    demo.launch(server_name="0.0.0.0", server_port=port)
