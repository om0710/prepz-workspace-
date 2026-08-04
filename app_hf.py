import os
import uvicorn
from app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"[HF SPACE] Starting Prepz AI server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
