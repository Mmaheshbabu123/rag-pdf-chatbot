from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import shutil
from typing import List, Optional
from sqlalchemy.orm import Session
from rag import process_pdf_and_store, ask_question, FAISS_INDEX_PATH
from database import get_db, ChatSession, ChatMessage

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

class Question(BaseModel):
    text: str
    session_id: Optional[int] = None

@app.get("/files")
async def list_files():
    files = [f for f in os.listdir(DATA_DIR) if f.endswith('.pdf')]
    return {"files": files}

@app.delete("/files/{filename}")
async def delete_file(filename: str):
    try:
        file_path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        os.remove(file_path)
        if os.path.exists(FAISS_INDEX_PATH):
            shutil.rmtree(FAISS_INDEX_PATH)
        remaining_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.pdf')]
        for f in remaining_files:
            process_pdf_and_store(os.path.join(DATA_DIR, f))
        return {"message": f"Successfully deleted {filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Chat History Endpoints ---

@app.get("/sessions")
async def get_sessions(db: Session = Depends(get_db)):
    sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()
    return sessions

@app.get("/sessions/{session_id}")
async def get_session_messages(session_id: int, db: Session = Depends(get_db)):
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc()).all()
    return messages

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"message": "Session deleted"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    file_path = os.path.join(DATA_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    try:
        num_chunks = process_pdf_and_store(file_path)
        return {"message": f"Successfully uploaded and processed {file.filename}", "chunks": num_chunks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(question: Question, db: Session = Depends(get_db)):
    try:
        # 1. Get or Create Session
        session_id = question.session_id
        if not session_id:
            # Create a new session with a title based on the first 30 chars of the question
            title = question.text[:30] + "..." if len(question.text) > 30 else question.text
            new_session = ChatSession(title=title)
            db.add(new_session)
            db.commit()
            db.refresh(new_session)
            session_id = new_session.id
        
        # 2. Get AI Answer
        response = ask_question(question.text)
        
        # 3. Save User Message
        user_msg = ChatMessage(session_id=session_id, role="user", text=question.text)
        db.add(user_msg)
        
        # 4. Save Bot Message
        bot_msg = ChatMessage(
            session_id=session_id,
            role="bot",
            text=response["answer"],
            sources=response["sources"],
            excerpts=response.get("excerpts", []),
        )
        db.add(bot_msg)

        db.commit()

        return {
            "answer": response["answer"],
            "sources": response["sources"],
            "excerpts": response.get("excerpts", []),
            "session_id": session_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Hugging Face Spaces (and most hosts) inject the port via $PORT; HF expects
    # 7860. Fall back to 8000 for local development.
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
