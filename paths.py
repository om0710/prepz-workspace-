import os


def _detect_data_dir():
    """Hugging Face Spaces Persistent Storage, when enabled on the Space, is mounted
    at /data and survives rebuilds/restarts. Use it when present and writable so the
    SQLite DB, uploaded files, and the Chroma vector store all persist; otherwise fall
    back to the repo's own working directory (e.g. for local development, or a Space
    without Persistent Storage enabled -- in which case this data stays ephemeral
    exactly as before)."""
    if os.path.isdir("/data"):
        try:
            probe = os.path.join("/data", ".write_test")
            with open(probe, "w") as f:
                f.write("ok")
            os.remove(probe)
            return "/data"
        except Exception:
            pass
    return "."


DATA_DIR = _detect_data_dir()
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")
DB_PATH = os.path.join(DATA_DIR, "chatbot.db")

os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(CHROMA_DIR, exist_ok=True)
