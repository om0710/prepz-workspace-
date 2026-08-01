import spaces
import uvicorn
from app import app

@spaces.GPU
def dummy_gpu_func():
    pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)
