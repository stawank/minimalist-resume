from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.llms import LlamaCpp
from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain.prompts import PromptTemplate
from pydantic import BaseModel

MODEL_PATH = "/home/stawan/.cache/llama.cpp/bartowski_Llama-3.2-1B-Instruct-GGUF_Llama-3.2-1B-Instruct-Q4_K_M.gguf"
DB_PATH = "/home/stawan/minimalist-resume/backend/chroma_db"

print("Loading resume memory...")
embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
vector_db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)

print("Loading Llama-3.2 brain...")
llm = LlamaCpp(
    model_path=MODEL_PATH,
    n_ctx=2048,
    n_batch=128,
    n_threads=4,
    temperature=0.1,
    verbose=False,
)

prompt_template = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are a professional assistant on Stawan Kulkarni's resume website.
Rules:
- Detect the language of the question and reply in the SAME language
- Use ONLY information from the context below
- If the context does not contain the answer, say so in the same language as the question
- Be concise, friendly and professional
- Never make up information
<|eot_id|><|start_header_id|>user<|end_header_id|>
Context:
{context}

Question: {question}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

PROMPT = PromptTemplate(
    template=prompt_template,
    input_variables=["context", "question"]
)

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vector_db.as_retriever(search_kwargs={"k": 5}),
    chain_type_kwargs={"prompt": PROMPT},
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
    result = qa_chain.invoke({"query": req.question})
    return ChatResponse(answer=result["result"].strip())

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
