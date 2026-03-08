from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.llms import LlamaCpp
from langchain.prompts import PromptTemplate
from pydantic import BaseModel
from datetime import datetime
from dotenv import load_dotenv
import openpyxl
from functools import lru_cache
import hashlib
from fastapi.responses import StreamingResponse
import json
import os
from langchain_google_genai import ChatGoogleGenerativeAI

MODEL_PATH = os.getenv("MODEL_PATH")
DB_PATH    = os.getenv("DB_PATH")
LOG_PATH   = os.getenv("LOG_PATH")
GEMINI_API_KEY = os.getenv("OPENROUTER_API_KEY")


print("Loading resume memory...")
embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
vector_db  = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)

print("Loading Gemini-3-flash brain...")
llm = ChatGoogleGenerativeAI(model="gemini-3-flash",
google_api_key=GEMINI_API_KEY,
temperature= 0.0)

prompt_template = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are a factual assistant on Stawan Kulkarni's resume website.
STRICT RULES:
- Answer ONLY using facts explicitly stated in the context below
- Detect question language and reply in SAME language
- If the answer is NOT explicitly in the context, reply ONLY with: "I don't have that information."
- Do NOT guess, infer, or make up anything
- Do NOT mention other people not related to Stawan Kulkarni
- Keep answers short and factual
- Keep answers under 3 sentences, no bullet points unless listing skills
- Stawan's surname is Kulkarni
- Never calculate or add up years from dates — only state what is explicitly written
<|eot_id|><|start_header_id|>user<|end_header_id|>
Context:
{context}

Question: {question}
<|eot_id|><|start_header_id|>assistant<|end_header_id|>
Answer:"""

PROMPT = PromptTemplate(
    template=prompt_template,
    input_variables=["context", "question"]
)
BLOCKED_SOURCES = {

    "FINAL DEGREE CERTIFICATE (1).pdf",
}
# ── Excel logger ──────────────────────────────────────────────────────────────
def log_to_excel(question: str, answer: str):
    try:
        if os.path.exists(LOG_PATH):
            wb = openpyxl.load_workbook(LOG_PATH)
            ws = wb.active
        else:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "HR Questions"
            ws.append(["Timestamp", "Question", "Answer"])
            for cell in ws[1]:
                cell.font = openpyxl.styles.Font(bold=True)
        ws.append([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), question, answer])
        wb.save(LOG_PATH)
    except Exception as e:
        print(f"Excel log error: {e}")

# ── Hallucination filter ──────────────────────────────────────────────────────
def validate_answer(answer: str, context: str) -> str:
    if len(answer) > 500:
        answer = answer[:500] + "..."
    context_words = set(context.lower().split())
    answer_words  = set(answer.lower().split())
    overlap = context_words & answer_words
    if len(overlap) < 3 and len(answer) > 100:
        return "I don't have that information."
    return answer

# ── Schemas ───────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str

# ── App ───────────────────────────────────────────────────────────────────────
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
    docs    = vector_db.similarity_search(req.question, k=5)
    context = "\n\n".join([d.page_content for d in docs])
    filled  = prompt_template.replace("{context}", context).replace("{question}", req.question)
    raw     = llm.invoke(filled).strip()
    answer  = validate_answer(raw, context)
    log_to_excel(req.question, answer)
    return ChatResponse(answer=answer)

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.get("/download-questions")
def download_questions():
    if os.path.exists(LOG_PATH):
        return FileResponse(LOG_PATH, filename="hr_questions.xlsx")
    return {"error": "No questions logged yet"}



# Cache last 50 unique questions
@lru_cache(maxsize=50)
def cached_rag(question_hash: str, question: str):
    docs = vector_db.similarity_search(question, k=5)
    context = "\n\n".join([d.page_content for d in docs])
    filled  = prompt_template.replace("{context}", context).replace("{question}", question)
    raw     = llm.invoke(filled).strip()
    return validate_answer(raw, context)

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    question_hash = hashlib.md5(req.question.lower().strip().encode()).hexdigest()
    answer = cached_rag(question_hash, req.question)
    log_to_excel(req.question, answer)
    return ChatResponse(answer=answer)#

@app.post("/chat/stream")
def chat_stream(req: ChatRequest):
    docs    = vector_db.similarity_search(req.question, k=5)
    # Filter blocked sources
    safe_docs = [d for d in docs if d.metadata.get("source", "") not in BLOCKED_SOURCES]
    if not safe_docs:
        def empty():
            yield f"data: {json.dumps({'token': 'I dont have that information.'})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(empty(), media_type="text/event-stream")

    context = "\n\n".join([d.page_content for d in safe_docs])
    filled  = prompt_template.replace("{context}", context).replace("{question}", req.question)

    def generate():
        full_answer = ""
        for token in llm.stream(filled):
            full_answer += token
            yield f"data: {json.dumps({'token': token})}\n\n"
        log_to_excel(req.question, full_answer.strip())
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")