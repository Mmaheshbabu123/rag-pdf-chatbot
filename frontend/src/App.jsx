import { useState, useEffect } from 'react';
import axios from 'axios';
import Modal from './components/atoms/Modal';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [chatting, setChatting] = useState(false);
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [status, setStatus] = useState('');
  const [indexedFiles, setIndexedFiles] = useState([]);
  const [activeSources, setActiveSources] = useState([]);
  
  // History state
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [fileToDelete, setFileToDelete] = useState(null);

  useEffect(() => {
    fetchFiles();
    fetchSessions();
  }, []);

  const fetchFiles = async () => {
    try {
      const response = await axios.get('http://localhost:8000/files');
      setIndexedFiles(response.data.files);
    } catch (err) {
      console.error("Failed to fetch files", err);
    }
  };

  const fetchSessions = async () => {
    try {
      const response = await axios.get('http://localhost:8000/sessions');
      setSessions(response.data);
    } catch (err) {
      console.error("Failed to fetch sessions", err);
    }
  };

  const loadSession = async (sessionId) => {
    try {
      const response = await axios.get(`http://localhost:8000/sessions/${sessionId}`);
      setMessages(response.data);
      setCurrentSessionId(sessionId);
      setActiveSources([]); // Reset highlights
    } catch (err) {
      console.error("Failed to load session", err);
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setCurrentSessionId(null);
    setActiveSources([]);
  };

  const deleteSession = async (e, sessionId) => {
    e.stopPropagation(); // Prevent loading the session
    if (!window.confirm("Delete this chat history?")) return;
    try {
      await axios.delete(`http://localhost:8000/sessions/${sessionId}`);
      if (currentSessionId === sessionId) startNewChat();
      fetchSessions();
    } catch (err) {
      console.error("Failed to delete session", err);
    }
  };

  const openDeleteModal = (filename) => {
    setFileToDelete(filename);
    setIsModalOpen(true);
  };

  const handleConfirmDelete = async () => {
    if (!fileToDelete) return;
    try {
      await axios.delete(`http://localhost:8000/files/${fileToDelete}`);
      setMessages((prev) => [...prev, { role: 'system', text: `Removed "${fileToDelete}" from knowledge base.` }]);
      fetchFiles();
    } catch (err) {
      alert("Failed to delete file");
    } finally {
      setIsModalOpen(false);
      setFileToDelete(null);
    }
  };

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const uploadFile = async () => {
    if (!file) return alert('Please select a file');
    setUploading(true);
    setStatus('Uploading and processing...');
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post('http://localhost:8000/upload', formData);
      setStatus(response.data.message);
      setMessages((prev) => [...prev, { role: 'system', text: `Added "${file.name}" to knowledge base.` }]);
      setTimeout(() => fetchFiles(), 500);
    } catch (err) {
      console.error(err);
      setStatus('Upload failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setUploading(false);
    }
  };

  const askQuestion = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    const userMsg = { role: 'user', text: question };
    setMessages([...messages, userMsg]);
    setQuestion('');
    setChatting(true);
    setActiveSources([]);

    try {
      const response = await axios.post('http://localhost:8000/chat', { 
        text: question,
        session_id: currentSessionId 
      });
      
      const { answer, sources, session_id } = response.data;
      
      if (!currentSessionId) {
        setCurrentSessionId(session_id);
        fetchSessions();
      }

      setMessages((prev) => [...prev, { 
        role: 'bot', 
        text: answer, 
        sources: sources 
      }]);
      
      // Smart highlighting logic
      let highlight = sources[0];
      for (let s of sources) {
        if (answer.toLowerCase().includes(s.toLowerCase().replace('.pdf', ''))) {
          highlight = s;
          break;
        }
      }
      if (highlight) setActiveSources([highlight]);
      
    } catch (err) {
      console.error(err);
      setMessages((prev) => [...prev, { role: 'bot', text: 'Error: ' + (err.response?.data?.detail || err.message) }]);
    } finally {
      setChatting(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Multi-PDF RAG Chatbot</h1>
        <button className="btn-new-chat" onClick={startNewChat}>+ New Chat</button>
      </header>

      <main>
        <div className="sidebar">
          <div className="sidebar-section">
            <h3>📂 Documents</h3>
            <input type="file" onChange={handleFileChange} accept=".pdf" />
            <button onClick={uploadFile} disabled={uploading || !file}>
              {uploading ? 'Processing...' : 'Add to Knowledge'}
            </button>
            <p className="status">{status}</p>
          </div>

          <div className="sidebar-section knowledge-base">
            <h3>🧠 Knowledge Base</h3>
            <ul>
              {indexedFiles.map((f, i) => (
                <li key={i} className={`kb-item ${activeSources.includes(f) ? 'highlighted' : ''}`}>
                  <span>📄 {f}</span>
                  <button className="btn-icon" onClick={() => openDeleteModal(f)}>🗑️</button>
                </li>
              ))}
            </ul>
          </div>

          <div className="sidebar-section history">
            <h3>🕒 Chat History</h3>
            <div className="history-list">
              {sessions.map((s) => (
                <div 
                  key={s.id} 
                  className={`history-item ${currentSessionId === s.id ? 'active' : ''}`}
                  onClick={() => loadSession(s.id)}
                >
                  <span className="history-title">{s.title}</span>
                  <button className="btn-icon" onClick={(e) => deleteSession(e, s.id)}>×</button>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="chat-section">
          <h3>💬 {currentSessionId ? 'Current Chat' : 'New Chat'}</h3>
          <div className="chat-window">
            {messages.length === 0 && <p className="placeholder">Ask a question about your documents!</p>}
            {messages.map((msg, i) => (
              <div key={i} className={`message ${msg.role}`}>
                <strong>{msg.role === 'user' ? 'You: ' : msg.role === 'bot' ? 'Bot: ' : ''}</strong>
                <span>{msg.text}</span>
                {msg.sources && msg.sources.length > 0 && (
                  <div className="message-sources">
                    Sources: {msg.sources.join(', ')}
                  </div>
                )}
              </div>
            ))}
            {chatting && <div className="message bot">Thinking...</div>}
          </div>
          
          <form onSubmit={askQuestion} className="chat-input">
            <input 
              type="text" 
              value={question} 
              onChange={(e) => setQuestion(e.target.value)} 
              placeholder="Ask anything..."
              disabled={uploading}
            />
            <button type="submit" disabled={chatting || uploading}>Send</button>
          </form>
        </div>
      </main>

      <Modal 
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onConfirm={handleConfirmDelete}
        title="Delete Document"
        message={`Are you sure you want to delete "${fileToDelete}"? This action cannot be undone.`}
      />
    </div>
  );
}

export default App;
