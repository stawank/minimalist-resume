import os
import shutil
import requests
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from bs4 import BeautifulSoup

DOCS_PATH    = os.path.expanduser("~/resume_docs")
DB_PATH      = os.path.expanduser("~/minimalist-resume/backend/chroma_db")
WEBSITE_HTML = "/var/www/minimalist-resume/index.html"
GITHUB_USER  = "stawank"
CHUNK_SIZE   = 300
CHUNK_OVERLAP = 30

SKIP_PDFS = {

    "Bachelor_Thesis_Report.pdf",
    "stawan-master-thesis-presentation.pdf",
    "DAQ File_2019.pdf",
    "DAQ Design report sample_2020.pdf",
}

splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

if os.path.exists(DB_PATH):
    shutil.rmtree(DB_PATH)
    print("Cleared old database.")

print("Loading embeddings model...")
embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
total_chunks = 0

# 1. Website
if os.path.exists(WEBSITE_HTML):
    print(f"\nLoading website: {WEBSITE_HTML}")
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
    print(f"   {len(chunks)} chunks from website")
else:
    print(f"Website not found at {WEBSITE_HTML}, skipping.")

# 2. PDFs
if os.path.exists(DOCS_PATH):
    pdfs = [f for f in os.listdir(DOCS_PATH) if f.endswith(".pdf")]
    print(f"\nFound {len(pdfs)} PDFs...")
    for filename in sorted(pdfs):
        if filename in SKIP_PDFS:
            print(f"   Skipping: {filename}")
            continue
        path = os.path.join(DOCS_PATH, filename)
        try:
            loader = PyPDFLoader(path)
            docs = loader.load()
            chunks = splitter.split_documents(docs)
            db.add_documents(chunks)
            total_chunks += len(chunks)
            print(f"   OK {filename} -> {len(chunks)} chunks")
        except Exception as e:
            print(f"   FAIL {filename} -> {e}")

# 3. GitHub
print(f"\nFetching GitHub: {GITHUB_USER}")
try:
    headers = {"Accept": "application/vnd.github+json"}
    profile = requests.get(f"https://api.github.com/users/{GITHUB_USER}", headers=headers, timeout=10).json()
    profile_text = f"""GitHub Profile: {profile.get('name', GITHUB_USER)}
Bio: {profile.get('bio', 'N/A')}
Location: {profile.get('location', 'N/A')}
Public Repositories: {profile.get('public_repos', 0)}
GitHub URL: {profile.get('html_url', '')}
"""
    repos = requests.get(f"https://api.github.com/users/{GITHUB_USER}/repos?per_page=100&sort=updated", headers=headers, timeout=10).json()
    repo_texts = []
    for r in repos:
        if r.get("fork"):
            continue
        repo_text = f"""Repository: {r['name']}
Description: {r.get('description') or 'No description'}
Language: {r.get('language') or 'N/A'}
URL: {r.get('html_url', '')}
"""
        readme_res = requests.get(
            f"https://api.github.com/repos/{GITHUB_USER}/{r['name']}/readme",
            headers={**headers, "Accept": "application/vnd.github.raw"},
            timeout=10
        )
        if readme_res.ok:
            repo_text += f"README:\n{readme_res.text[:800]}\n"
        repo_texts.append(repo_text)
        print(f"   OK {r['name']}")
    all_github = profile_text + "\n\n" + "\n\n".join(repo_texts)
    doc = Document(page_content=all_github, metadata={"source": "github"})
    chunks = splitter.split_documents([doc])
    db.add_documents(chunks)
    total_chunks += len(chunks)
    print(f"   {len(chunks)} chunks from GitHub ({len(repo_texts)} repos)")
except Exception as e:
    print(f"   GitHub failed: {e}")

# 4. Ingest TXT files
txt_files = [f for f in os.listdir(DOCS_PATH) if f.endswith(".txt")]
print(f"\nFound {len(txt_files)} TXT files...")
for filename in sorted(txt_files):
    path = os.path.join(DOCS_PATH, filename)
    try:
        with open(path, "r") as f:
            text = f.read()
        doc = Document(page_content=text, metadata={"source": filename})
        chunks = splitter.split_documents([doc])
        db.add_documents(chunks)
        total_chunks += len(chunks)
        print(f"   OK {filename} -> {len(chunks)} chunks")
    except Exception as e:
        print(f"   FAIL {filename} -> {e}")
print(f"\nDone! {total_chunks} total chunks stored.")
