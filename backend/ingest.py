import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# 1. Setup paths
DOCS_PATH = os.path.expanduser("~/resume_docs")
DB_PATH = os.path.expanduser("~/minimalist-resume/backend/chroma_db")

# 2. Load PDFs from your folder
print(f"Searching for PDFs in {DOCS_PATH}...")
documents = []
if not os.path.exists(DOCS_PATH):
    os.makedirs(DOCS_PATH)
    print(f"Created {DOCS_PATH}. Please put your PDFs there and run again.")
    exit()

for file in os.listdir(DOCS_PATH):
    if file.endswith(".pdf"):
        print(f"Loading {file}...")
        loader = PyPDFLoader(os.path.join(DOCS_PATH, file))
        documents.extend(loader.load())

if not documents:
    print("No PDFs found! Add your resume to ~/resume_docs first.")
    exit()

# 3. Split text into manageable chunks for the Pi's RAM
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = text_splitter.split_documents(documents)

# 4. Create Embeddings (Math version of your text)
print("Downloading embedding model (MiniLM)...")
model_kwargs = {'device': 'cpu'}
encode_kwargs = {'normalize_embeddings': False}
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2", 
    model_kwargs=model_kwargs,
    encode_kwargs=encode_kwargs)

# 5. Save to Vector Database
print(f"Creating database at {DB_PATH}...")
vector_db = Chroma.from_documents(
    documents=chunks, 
    embedding=embeddings, 
    persist_directory=DB_PATH
)
print("✅ Done! Your resume is now indexed.")