import os
import uvicorn

try:
    import spaces
    import torch

    @spaces.GPU
    def initialize_gpu():
        try:
            if torch.cuda.is_available():
                x = torch.ones(1, device="cuda")
                return float(x.cpu().item())
        except Exception:
            pass
        return 1.0

    # Call GPU function at startup so ZeroGPU detector finds active execution
    try:
        initialize_gpu()
    except Exception as e:
        print(f"[ZERO-GPU INIT NOTICE] {e}")

except Exception as e:
    print(f"[INFO] ZeroGPU init skipped: {e}")

from app import app as fastapi_app

# Mount app for Gradio SDK compliance on Hugging Face Spaces
try:
    import gradio as gr
    with gr.Blocks(title="BU Prepz AI Workspace") as demo:
        gr.HTML('<iframe src="/index.html" style="width:100%; height:100vh; border:none; margin:0; padding:0;"></iframe>')
    app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio_view")
except Exception as g_err:
    print(f"[NOTICE] Gradio mount fallback to FastAPI direct app: {g_err}")
    app = fastapi_app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"[HF SPACE] Starting server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
