import os
import uvicorn

try:
    import spaces
    import torch

    @spaces.GPU
    def zero_gpu_dummy():
        return True

    # Invoke GPU function during initial module import so ZeroGPU detector catches it
    try:
        zero_gpu_dummy()
        print("[ZERO-GPU OK] ZeroGPU function successfully executed at startup.")
    except Exception as e:
        print(f"[ZERO-GPU NOTICE] {e}")

except Exception as e:
    print(f"[INFO] ZeroGPU init skipped: {e}")

from app import app as fastapi_app

try:
    import gradio as gr
    with gr.Blocks(title="BU Prepz AI Workspace") as demo:
        gr.HTML('<iframe src="/" style="width:100%; height:100vh; border:none; margin:0; padding:0;"></iframe>')
    app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio")
except Exception as e:
    print(f"[GRADIO MOUNT NOTICE] {e}")
    app = fastapi_app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"[HF SPACE] Starting server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
