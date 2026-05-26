# 🔬 Technical Deep Dive: Database & Search Logic

## 1. The "Database" (FAISS) Connection
Unlike traditional databases (like MySQL or MongoDB), **FAISS (Facebook AI Similarity Search)** is a vector library that lives in your project as files.

*   **Connection Type:** It is a "File-Based" connection.
*   **Storage Location:** When you run the project, a folder named `faiss_index/` is created inside the `backend/` directory. Inside, you will see two files:
    *   `index.faiss`: Contains the mathematical "map" of your document.
    *   `index.pkl`: Contains the actual text snippets associated with those numbers.
*   **The Process:** Every time you ask a question, the code runs `FAISS.load_local()`. This loads the map into your computer's RAM (memory) so the search is instantaneous (micro-seconds).

---

## 2. Step-by-Step: When you Upload a PDF
When you click "Upload & Index" in the UI, this 7-step chain reaction occurs:

1.  **Transmission:** The React Frontend sends the PDF file to the Backend via a `POST /upload` request using `FormData`.
2.  **Physical Save:** The Backend receives the file and saves a copy in the `backend/data/` folder. This is your "source of truth."
3.  **Extraction:** `PyPDFLoader` opens the file and reads every character, converting the PDF pages into raw Python strings.
4.  **Chunking:** The `RecursiveCharacterTextSplitter` slices the text. If you have 10,000 characters, it creates roughly 11 chunks (1,000 chars each with 100 char overlap).
5.  **Embedding (The Numbers):** Each chunk is sent to the **HuggingFace Embedding model**. It converts the text "Hello world" into a vector (e.g., `[0.1, -0.5, 0.2...]`).
6.  **Indexing:** These vectors are added to the FAISS index. Think of this like putting points on a 3D graph.
7.  **Serialization:** The index is "saved to disk" in the `faiss_index/` folder. The system is now "trained" on your document.

---

## 3. Step-by-Step: The Search & Chatbot Logic
When you type a question like *"What is the summary of this file?"*, here is how the AI finds the answer:

1.  **Question Embedding:** The system converts your *question* into a vector using the same HuggingFace model. 
2.  **Vector Comparison:** It looks at the "3D map" in FAISS and finds the 3 chunks of text whose vectors are mathematically closest to your question's vector.
3.  **Context Assembly:** The text from those 3 chunks is pulled out and joined together into one long string called "The Context."
4.  **Prompt Engineering:** The system builds a "Master Prompt" for the AI:
    > "You are a helpful assistant. Here is some data from a PDF: [CONTEXT]. Now, answer this question: [QUESTION]."
5.  **Groq LLM Call:** This Master Prompt is sent to **Groq (Llama 3.3)**.
6.  **Response:** The AI reads the provided context, ignores everything else it knows, and generates a concise answer based *only* on that data.
7.  **Delivery:** The answer is sent back through the API and displayed in your React chat bubble.
