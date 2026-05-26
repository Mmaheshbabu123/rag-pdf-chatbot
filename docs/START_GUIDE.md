# 🚀 How to Start the Project

Follow these steps to get your RAG PDF Chatbot up and running.

## 1. Start the Backend (The API)
Open a terminal and run the following:

```bash
cd backend
source venv/bin/activate
python main.py
```
*   **What this does:** Activates your Python environment and starts the FastAPI server at `http://localhost:8000`.
*   **Keep this terminal open!** If you close it, the chatbot's "brain" will stop working.

## 2. Start the Frontend (The UI)
Open a **second** terminal window or tab and run:

```bash
cd frontend
npm run dev
```
*   **What this does:** Starts the React development server.
*   **URL:** It will provide a link, usually `http://localhost:5173`.

## 3. Access the Application
1.  Open your web browser.
2.  Go to `http://localhost:5173`.
3.  Upload a PDF or continue chatting with previously indexed documents!

---

## 💡 Pro-Tips for Tomorrow
*   **Saved Data:** You do NOT need to re-upload PDFs you processed today. The database is saved in the `backend/faiss_index/` folder.
*   **API Key:** Ensure your `backend/.env` file still contains your valid `GROQ_API_KEY`.
*   **Error?** If you see a "Failed to connect" error in the browser, check that the **Backend terminal** is still running and didn't crash.
