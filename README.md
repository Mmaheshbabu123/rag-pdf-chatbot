# RAG PDF Chatbot

A full-stack application that allows users to upload PDF documents and interact with them using an AI chatbot. It uses Retrieval-Augmented Generation (RAG) to ensure the AI's answers are based directly on the uploaded documents, complete with source citations.

## Features

*   **PDF Upload & Processing:** Upload multiple PDF documents.
*   **Knowledge Base Management:** View and delete indexed documents. The system automatically re-indexes when files are removed.
*   **Interactive Chat:** Ask questions and get answers derived from your documents.
*   **Source Citations:** The chatbot highlights which documents it used to formulate its answer.
*   **Chat History:** Conversations are saved so you can revisit past sessions.

## Tech Stack

*   **Frontend:** React (Vite)
*   **Backend:** FastAPI (Python)
*   **RAG/AI:** LangChain, FAISS (Vector DB), HuggingFace Embeddings (`all-MiniLM-L6-v2`)
*   **LLM:** Groq (`llama-3.3-70b-versatile`)
*   **Database:** SQLite (for chat history)

## Setup Instructions

### 1. Backend Setup

1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```
2.  Create a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Set up your environment variables:
    *   Create a `.env` file in the `backend` directory.
    *   Add your Groq API key: `GROQ_API_KEY=your_api_key_here`
5.  Start the backend server:
    ```bash
    python main.py
    ```
    The API will be available at `http://localhost:8000`.

### 2. Frontend Setup

1.  Navigate to the frontend directory:
    ```bash
    cd frontend
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Start the development server:
    ```bash
    npm run dev
    ```
    The application will be available at `http://localhost:5173`.
