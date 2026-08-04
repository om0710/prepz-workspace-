import os
import uvicorn

try:
    import spaces
    import gradio as gr

    @spaces.GPU
    def gpu_function(text: str) -> str:
        """ZeroGPU bound function to satisfy HuggingFace startup requirement"""
        return text

    with gr.Blocks() as demo:
        gr.Markdown("### Prepz AI Workspace Backend")
        txt_in = gr.Textbox(visible=False)
        txt_out = gr.Textbox(visible=False)
        dummy_btn = gr.Button("Initialize", visible=False)
        dummy_btn.click(gpu_function, inputs=txt_in, outputs=txt_out)

    from app import app as fastapi_app
    app = gr.mount_gradio_app(fastapi_app, demo, path="/_gradio")

except Exception as e:
    print(f"[NOTICE] Running without Gradio ZeroGPU wrapper: {e}")
    from app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
