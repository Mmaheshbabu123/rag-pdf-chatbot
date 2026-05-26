import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

FAISS_INDEX_PATH = "faiss_index"

def get_embeddings():
    # Free local embeddings (runs on CPU)
    return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def process_pdf_and_store(file_path: str):
    # Extract text from PDF
    loader = PyPDFLoader(file_path)
    documents = loader.load()
    
    # Split Text into Chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100
    )
    chunks = text_splitter.split_documents(documents)
    
    if not chunks:
        raise ValueError("The PDF contains no readable text or is too small to be indexed.")
    
    # Create or Load Embeddings + Store
    embeddings = get_embeddings()
    
    if os.path.exists(FAISS_INDEX_PATH):
        # Load existing index and add new chunks
        vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
        vectorstore.add_documents(chunks)
    else:
        # Create a new index
        vectorstore = FAISS.from_documents(chunks, embeddings)
    
    # Save the updated index locally
    vectorstore.save_local(FAISS_INDEX_PATH)
    
    return len(chunks)

def ask_question(question: str):
    # Load vectorstore
    embeddings = get_embeddings()
    
    if not os.path.exists(FAISS_INDEX_PATH):
        return {"answer": "Please upload a document first.", "sources": []}
        
    vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    
    # Question Answering using Groq (Llama 3)
    llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0)
    
    system_prompt = (
        "You are a helpful assistant for question-answering tasks. "
        "Use the provided context to answer the question. "
        "Always mention which document the information came from in your answer. "
        "If you truly don't know, say you don't know. "
        "Keep it concise (max 3 sentences)."
        "\n\n"
        "{context}"
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )
    
    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    # We use search_kwargs={"k": 3} to ensure the AI finds the correct information
    rag_chain = create_retrieval_chain(vectorstore.as_retriever(search_kwargs={"k": 3}), question_answer_chain)
    
    response = rag_chain.invoke({"input": question})
    
    # Extract filenames from retrieved documents while preserving order (rank)
    sources = []
    for doc in response["context"]:
        source_name = os.path.basename(doc.metadata.get('source', 'Unknown'))
        if source_name not in sources:
            sources.append(source_name)
    
    return {"answer": response["answer"], "sources": sources}
