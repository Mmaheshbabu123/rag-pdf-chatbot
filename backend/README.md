# RAG PDF Chatbot — Backend API

FastAPI backend for the RAG PDF Chatbot. Users upload PDFs; the service embeds
them with `BAAI/bge-small-en-v1.5` (via `fastembed`/ONNX — lightweight, no
PyTorch), stores vectors in FAISS, and answers questions with Groq, returning
verbatim excerpts and page citations.

Deployed as a Docker web service on Render. Listens on `$PORT` (injected by the
host); falls back to `8000` locally.

## Required environment variable

- `GROQ_API_KEY` — your Groq API key. Set it in the Render dashboard
  (Environment → Add Environment Variable).

## Note on storage

Render's free tier uses ephemeral disk: uploaded PDFs, the FAISS index and chat
history reset when the service restarts or redeploys.
