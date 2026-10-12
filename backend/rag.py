import os
import re
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

FAISS_INDEX_PATH = "faiss_index"

def get_embeddings():
    # Free local embeddings (runs on CPU). We use fastembed (ONNX runtime) rather
    # than sentence-transformers/PyTorch: same bge-small-en-v1.5 model and quality,
    # but a ~250MB footprint instead of ~1GB, so it fits on free hosting tiers.
    # fastembed normalizes bge embeddings internally, so cosine search works.
    return FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")

# --- Noise filtering -------------------------------------------------------
# Front matter (ToC/preface), bibliographies and back-of-book indexes are dense
# keyword soup that pollutes semantic search without holding real answers. We
# drop those chunks at index time so they never compete with content pages.

_ROMAN = re.compile(r"^[ivxlcdm]+$", re.I)

def _normalize_ws(text):
    # Collapse whitespace/case so verbatim quotes match despite line breaks.
    return re.sub(r"\s+", " ", text).strip().lower()

def _looks_like_references(text):
    markers = len(re.findall(
        r"doi:|isbn|\bpages?\s+\d+|\[\d+\]|volume\s+\d+|proceedings|conference",
        text, re.I))
    return markers >= 4

def _looks_like_index(text):
    # Back-of-book index entries are packed with "term, 123, 456" page pointers.
    # Content pages top out at ~3 such patterns; index chunks have many more.
    entries = len(re.findall(r",\s*\d{1,4}\b", text))
    return entries >= 6

def _is_noise_chunk(doc):
    label = str(doc.metadata.get("page_label", ""))
    if _ROMAN.match(label) or label.lower() == "cover":  # front matter / cover
        return True
    text = doc.page_content
    return _looks_like_references(text) or _looks_like_index(text)

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
        # No extractable text usually means the PDF is a scan (images only).
        # PyPDFLoader has no OCR, so nothing can be indexed without it.
        raise ValueError(
            "No readable text found in this PDF. It looks like a scanned/image-only "
            "document, which needs OCR to be indexed. Please upload a text-based PDF."
        )

    # Drop front-matter / references / index chunks so they don't pollute search.
    chunks = [c for c in chunks if not _is_noise_chunk(c)]
    
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
        return {"answer": "Please upload a document first.", "sources": [], "excerpts": []}

    vectorstore = FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)

    # Plain similarity search (top k=8). We deliberately avoid MMR here: its
    # diversity re-ranking was pushing the single most-relevant passage out of
    # the results on this book. Precision matters more than diversity when the
    # goal is to surface the exact page that answers the question.
    retriever = vectorstore.as_retriever(search_kwargs={"k": 8})
    docs = retriever.invoke(question)

    # Build the exact excerpts (verbatim PDF text + real page number from the
    # PDF's own metadata) and a context string where every chunk is prefixed
    # with its source + page, so the model cites the correct page instead of
    # guessing one from the text.
    excerpts = []
    context_parts = []
    sources = []
    for doc in docs:
        name = os.path.basename(doc.metadata.get("source", "Unknown"))
        # Prefer the PDF's printed page label (matches what the reader sees);
        # fall back to the 1-based physical page index.
        page = doc.metadata.get("page")
        page_num = doc.metadata.get("page_label")
        if not page_num and isinstance(page, int):
            page_num = page + 1
        text = doc.page_content.strip()

        excerpts.append({"source": name, "page": page_num, "text": text})

        label = f"{name} (p. {page_num})" if page_num else name
        if label not in sources:
            sources.append(label)

        header = f"[{name}, page {page_num}]" if page_num else f"[{name}]"
        context_parts.append(f"{header}\n{text}")

    context = "\n\n---\n\n".join(context_parts)

    llm = ChatGroq(model_name="openai/gpt-oss-120b", temperature=0)

    system_prompt = (
        "You answer questions using ONLY the provided context, which contains "
        "excerpts taken directly from PDF documents. Each excerpt begins with a "
        "header in square brackets giving its source file and page number.\n"
        "Rules:\n"
        "1. Quote the relevant text VERBATIM (word-for-word) from the context, "
        "inside quotation marks, so the user sees exactly what the PDF says.\n"
        "2. You may add a short clarification after the quote, but do not "
        "paraphrase away the original wording.\n"
        "3. Always cite the exact page number shown in the excerpt header. "
        "NEVER invent, guess, or change a page number.\n"
        "4. If the context does not contain the answer, say you don't know."
    )
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "Context:\n\n{context}\n\nQuestion: {input}"),
        ]
    )

    response = (prompt | llm).invoke({"context": context, "input": question})
    answer = response.content if hasattr(response, "content") else str(response)

    # Pin the citation to the page(s) whose text the answer actually quoted,
    # instead of listing every retrieved page. We detect which excerpts the
    # answer reused by looking for their text inside the answer (whitespace-
    # normalised), so the page number is precise to the quoted content.
    answer_norm = _normalize_ws(answer)
    used = []
    for ex in excerpts:
        ex_norm = _normalize_ws(ex["text"])
        probe = 40  # a 40-char snippet is enough to confirm a verbatim reuse
        for i in range(0, max(1, len(ex_norm) - probe), 20):
            if ex_norm[i:i + probe] in answer_norm:
                used.append(ex)
                break

    if used:
        # Precise: only the pages actually quoted, and show those excerpts first.
        precise_sources = []
        for ex in used:
            label = f"{ex['source']} (p. {ex['page']})" if ex["page"] else ex["source"]
            if label not in precise_sources:
                precise_sources.append(label)
        sources = precise_sources
        # Show only the excerpts the answer actually quoted, not all 8 retrieved.
        excerpts = used

    return {"answer": answer, "sources": sources, "excerpts": excerpts}
