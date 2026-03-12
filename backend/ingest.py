import os
import shutil
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from bs4 import BeautifulSoup
from gitingest import ingest

DOCS_PATH    = os.path.expanduser("~/resume_docs")
DB_PATH      = os.path.expanduser("~/minimalist-resume/backend/chroma_db")
WEBSITE_HTML = "/var/www/minimalist-resume/index.html"
CHUNK_SIZE   = 500
CHUNK_OVERLAP = 50

SKIP_PDFS = {
    "Bachelor_Thesis_Report.pdf",
    "stawan-master-thesis-presentation.pdf",
    "DAQ File_2019.pdf",
    "DAQ Design report sample_2020.pdf",
}

GITHUB_REPOS = [
    "https://github.com/stawank/minimalist-resume",
    "https://github.com/stawank/TU_KL_SeminarElectromobility",
    "https://github.com/stawank/stawank.github.io",
    "https://github.com/stawank/ros2_playground",
]

# ── Setup ─────────────────────────────────────────────────────────────────────
splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP
)

if os.path.exists(DB_PATH):
    shutil.rmtree(DB_PATH)
    print("Cleared old database.")

print("Loading embeddings model...")
embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
total_chunks = 0

# ── 1. Website ────────────────────────────────────────────────────────────────
print(f"\n[1/4] Loading website: {WEBSITE_HTML}")
if os.path.exists(WEBSITE_HTML):
    with open(WEBSITE_HTML, "r") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    doc = Document(page_content=text, metadata={"source": "resume_website"})
    chunks = splitter.split_documents([doc])
    db.add_documents(chunks)
    total_chunks += len(chunks)
    print(f"   OK -> {len(chunks)} chunks")
else:
    print(f"   SKIP: not found at {WEBSITE_HTML}")

# ── 2. PDFs ───────────────────────────────────────────────────────────────────
print(f"\n[2/4] Loading PDFs from {DOCS_PATH}")
if os.path.exists(DOCS_PATH):
    pdfs = sorted([f for f in os.listdir(DOCS_PATH) if f.endswith(".pdf")])
    print(f"   Found {len(pdfs)} PDFs")
    for filename in pdfs:
        if filename in SKIP_PDFS:
            print(f"   SKIP: {filename}")
            continue
        path = os.path.join(DOCS_PATH, filename)
        try:
            loader = PyPDFLoader(path)
            docs = loader.load()
            chunks = splitter.split_documents(docs)
            db.add_documents(chunks)
            total_chunks += len(chunks)
            print(f"   OK: {filename} -> {len(chunks)} chunks")
        except Exception as e:
            print(f"   FAIL: {filename} -> {e}")
else:
    print(f"   SKIP: {DOCS_PATH} not found")

# ── 3. GitHub repos via GitIngest ─────────────────────────────────────────────
print(f"\n[3/4] Ingesting GitHub repos via GitIngest...")
for repo_url in GITHUB_REPOS:
    try:
        print(f"   Fetching {repo_url}...")
        summary, tree, content = ingest(
            repo_url,
            max_file_size=50000,
            include_patterns={"*.py", "*.md", "*.txt", "*.js", "*.html", "*.css"},
        )
        full_text = f"GitHub Repository: {repo_url}\n\nSummary:\n{summary}\n\nFile Tree:\n{tree}\n\nContent:\n{content}"
        doc = Document(
            page_content=full_text,
            metadata={"source": "github", "url": repo_url}
        )
        chunks = splitter.split_documents([doc])
        db.add_documents(chunks)
        total_chunks += len(chunks)
        print(f"   OK: {repo_url.split('/')[-1]} -> {len(chunks)} chunks")
    except Exception as e:
        print(f"   FAIL: {repo_url} -> {e}")

# ── 4. TXT files ──────────────────────────────────────────────────────────────
print(f"\n[4/4] Loading TXT files from {DOCS_PATH}")
if os.path.exists(DOCS_PATH):
    txt_files = sorted([f for f in os.listdir(DOCS_PATH) if f.endswith(".txt")])
    print(f"   Found {len(txt_files)} TXT files")
    for filename in txt_files:
        path = os.path.join(DOCS_PATH, filename)
        try:
            with open(path, "r") as f:
                text = f.read()
            doc = Document(page_content=text, metadata={"source": filename})
            chunks = splitter.split_documents([doc])
            db.add_documents(chunks)
            total_chunks += len(chunks)
            print(f"   OK: {filename} -> {len(chunks)} chunks")
        except Exception as e:
            print(f"   FAIL: {filename} -> {e}")

print(f"\nDone! {total_chunks} total chunks stored in ChromaDB.")
