import os
import uvicorn
from app import app

try:
    import spaces
    @spaces.GPU
    def dummy_gpu_func():
        pass
except Exception:
    pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
