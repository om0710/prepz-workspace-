import os
import uvicorn
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
    print(f"ZeroGPU init notice: {e}")

from app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
