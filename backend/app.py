import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_community.llms import LlamaCpp
from langchain.chains.retrieval_qa.base import RetrievalQA

# 1. Paths
MODEL_PATH = "/home/stawan/.cache/llama.cpp/bartowski_Llama-3.2-1B-Instruct-GGUF_Llama-3.2-1B-Instruct-Q4_K_M.gguf"
DB_PATH = "/home/stawan/minimalist-resume/backend/chroma_db"

# 2. Load the Memory (ChromaDB)
print("Loading resume memory...")
embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
vector_db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)

# 3. Load the Brain (Llama-3.2)
print("Loading Llama-3.2 brain (this takes a moment)...")
llm = LlamaCpp(
    model_path=MODEL_PATH,
    n_ctx=2048,      # Context window for Pi 4
    n_batch= 128,
    n_threads=4,     # Use all 4 cores of the Pi 4
    temperature=0.1,
    verbose=False
)

# 4. Create the Question-Answer Chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vector_db.as_retriever(search_kwargs={"k": 2}) # Look at top 2 resume matches
)

# 5. The Chat Interface
print("\n--- Resume Chatbot Ready! ---")
while True:
    query = input("\nAsk about Stawan's resume (or 'exit'): ")
    if query.lower() == 'exit':
        break
    
    print("Thinking...")
    response = qa_chain.run(query)
    print(f"\nAI Response: {response}")