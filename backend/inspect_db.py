import pickle
import faiss
import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

# 1. Setup the same embedding model
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 2. Load the index
index_path = "faiss_index"
vectorstore = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)

# 3. Access the raw FAISS index (the numbers)
raw_index = vectorstore.index
num_vectors = raw_index.ntotal
dimensions = raw_index.d

print("--- 📊 DATABASE STATS ---")
print(f"Number of chunks stored: {num_vectors}")
print(f"Dimensions per vector: {dimensions} (each chunk is a list of {dimensions} numbers)")

print("\n--- 🧩 A LOOK AT THE VECTORS ---")
# Let's look at the first vector stored in the database
# We have to reconstruct it from the binary index
vector_sample = raw_index.reconstruct(0) 

print(f"First 10 numbers of the first vector:\n{vector_sample[:10]}...")
print("\n(Note: There are 374 more numbers after these that define the 'meaning' of the text!)")

print("\n--- 📝 THE CORRESPONDING TEXT ---")
# Let's see what text those numbers represent
# In FAISS, the 'docstore' maps IDs to the actual text chunks
first_id = vectorstore.index_to_docstore_id[0]
first_doc = vectorstore.docstore.search(first_id)
print(f"Text Content:\n\"{first_doc.page_content}\"")
