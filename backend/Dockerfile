FROM python:3.11-slim

# Model cache lives inside the image so there is no slow download on cold start.
# fastembed caches ONNX models under this dir.
ENV HF_HOME=/app/.cache \
    FASTEMBED_CACHE_PATH=/app/.cache/fastembed \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps: build tooling occasionally needed by faiss / tokenizers wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model at build time so the first request is fast.
RUN python -c "from langchain_community.embeddings import FastEmbedEmbeddings; FastEmbedEmbeddings(model_name='BAAI/bge-small-en-v1.5').embed_query('warmup')"

COPY . .

# The app writes the FAISS index, uploaded PDFs and chats.db at runtime, so make
# the working dir writable regardless of which UID the host runs the container as.
RUN chmod -R 777 /app

# The host (Render) injects $PORT at runtime; main.py reads it.
CMD ["python", "main.py"]
