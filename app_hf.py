import os
import spaces
import uvicorn
from app import app

@spaces.GPU(duration=60)
def zero_gpu_initializer():
    return "ZeroGPU Ready"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
