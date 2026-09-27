FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y     build-essential     sqlite3     && rm -rf /var/lib/apt/lists/*

# Set up non-root user for Hugging Face Spaces
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user     PATH=/home/user/.local/bin:$PATH     PYTHONUNBUFFERED=1

WORKDIR $HOME/app

# Copy requirements and install
COPY --chown=user:user requirements.txt $HOME/app/requirements.txt
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application files
COPY --chown=user:user . $HOME/app

# Ensure runtime directories exist with proper write permissions
RUN mkdir -p $HOME/app/uploads $HOME/app/chroma_db

EXPOSE 7860

CMD ["uvicorn", "app_hf:app", "--host", "0.0.0.0", "--port", "7860"]
