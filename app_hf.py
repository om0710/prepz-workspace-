import os
import uvicorn

# 1. Import spaces directly for HF ZeroGPU initialization
try:
    import spaces
except Exception:
    class _MockSpaces:
        def GPU(self, fn=None, duration=None, **kwargs):
            if fn is None:
                return lambda f: f
            return fn
    spaces = _MockSpaces()

import torch

# 2. Top-level @spaces.GPU decorated function required by HF ZeroGPU scanner
@spaces.GPU
def initialize_gpu(x: float = 1.0) -> float:
    try:
        if torch.cuda.is_available():
            tensor = torch.ones(1, device="cuda")
            return float(tensor.cpu().item())
    except Exception:
        pass
    return float(x)

# 3. Trigger GPU execution at startup so ZeroGPU detector marks initialization success
try:
    initialize_gpu()
except Exception as err:
    print(f"[ZeroGPU] Startup notice: {err}")

# 4. Import main FastAPI app
from app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)
