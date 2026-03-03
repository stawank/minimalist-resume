import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_community.llms import LlamaCpp
from langchain_community.vectorstores import Chroma
from langchain.chains.retrieval_qa.base import RetrievalQA
from pydantic import BaseModel

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
    n_ctx=2048,
    n_batch=128,
    n_threads=4,
    temperature=0.1,
    verbose=False,
)

# 4. Create the Question-Answer Chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vector_db.as_retriever(search_kwargs={"k": 2}),
)


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str


app = FastAPI(title="Minimalist Resume Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    answer = qa_chain.run(req.question)
    return ChatResponse(answer=answer)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}