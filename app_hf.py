import os
import uvicorn

try:
    import spaces
    import gradio as gr

    @spaces.GPU
    def gpu_zero_init(query: str = "") -> str:
        return query

    with gr.Blocks() as demo:
        gr.Markdown("# Prepz Workspace ZeroGPU Engine")
        t_in = gr.Textbox(visible=False)
        t_out = gr.Textbox(visible=False)
        btn = gr.Button("Init", visible=False)
        btn.click(fn=gpu_zero_init, inputs=t_in, outputs=t_out)

    from app import app as fastapi_app
    app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio")

except Exception as e:
    print(f"[INFO] Local or fallback execution notice: {e}")
    from app import app as fastapi_app
    app = fastapi_app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
