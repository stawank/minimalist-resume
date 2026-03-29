import os
import shutil
import requests
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from bs4 import BeautifulSoup
from gitingest import ingest

DOCS_PATH     = os.path.expanduser("~/resume_docs")
DB_PATH       = os.path.expanduser("~/minimalist-resume/backend/chroma_db")
CHUNK_SIZE    = 500
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

WEBSITE = [
    "https://www.stawank.cv",
    "https://www.stawank.cv/thesis.html",
    "https://www.stawank.cv/baja.html",
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
print(f"\n[1/4] Fetching website pages...")
for url in WEBSITE:
    try:
        print(f"   Fetching {url}...")
        response = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
        })
        soup = BeautifulSoup(response.content, "html.parser")
        title = soup.title.string if soup.title else ""
        for tag in soup(["script", "style", "img", "input"]):
            tag.decompose()
        body_text = soup.body.get_text(separator="\n", strip=True) if soup.body else ""
        text = (title + "\n\n" + body_text).strip()
        if not text:
            print(f"   SKIP: no content returned for {url}")
            continue
        doc = Document(
            page_content=text,
            metadata={"source": "website", "url": url}
        )
        chunks = splitter.split_documents([doc])
        db.add_documents(chunks)
        total_chunks += len(chunks)
        print(f"   OK: {url} -> {len(chunks)} chunks")
    except Exception as e:
        print(f"   FAIL: {url} -> {e}")

# ── 2. PDFs ───────────────────────────────────────────────────────────────────

BATCH_SIZE = 5

# Get list of all PDF files
pdf_files = [f for f in os.listdir(DOCS_PATH) if f.endswith('.pdf')]

for i in range(0, len(pdf_files), BATCH_SIZE):
    batch = pdf_files[i:i + BATCH_SIZE]
    batch_docs = []
    
    print(f"--- Processing batch {i//BATCH_SIZE + 1}: {batch} ---")
    
    for pdf_name in batch:
        loader = PyPDFLoader(os.path.join(DOCS_PATH, pdf_name))
        try:
            batch_docs.extend(loader.load_and_split())
        except Exception as e:
            print(f"Error loading {pdf_name}: {e}")

    if batch_docs:
        db.add_documents(batch_docs)
        print(f"Successfully indexed {len(batch_docs)} chunks from this batch.")
    
    del batch_docs

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