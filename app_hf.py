import os
import uvicorn
import gradio as gr

# Load FastAPI application instance
from app import app

# Create a Gradio Blocks instance 'demo' required by HuggingFace Gradio Space runner
with gr.Blocks(title="BU Prepz AI Workspace") as demo:
    gr.HTML('<script>window.location.href = "/";</script>')

# Mount gradio app instance
app = gr.mount_gradio_app(app, demo, path="/gradio")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"[HF SPACE] Starting server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
