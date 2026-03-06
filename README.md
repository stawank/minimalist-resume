# Minimalist Resume Website with Local LLM Chatbot

A personal resume website served from a Raspberry Pi with a fully offline AI chatbot powered by Llama 3.2. Recruiters can ask questions about my experience, skills, and projects directly on the site.

**Live:** [stawank.cv](https://stawank.cv)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, Vanilla JS |
| Web Server | Nginx |
| Backend | FastAPI (Python) |
| LLM | Llama 3.2 1B via llama.cpp |
| RAG | LangChain + ChromaDB |
| Embeddings | sentence-transformers (BAAI/bge-small-en-v1.5) |
| Tunnel | Cloudflare Tunnel / Tailscale Funnel |
| Hardware | Raspberry Pi 4 |

---

## Architecture

```
Visitor
  │
  ▼
stawank.cv
  │
  ▼
Tailscale Funnel (bypasses CG-NAT)
  │
  ▼
Nginx (port 80)
  ├── /          → serves static frontend
  └── /chat      → proxies to FastAPI (port 8000)
                      │
                      ├── ChromaDB (vector search)
                      │     └── resume docs + website + GitHub
                      │
                      └── Llama 3.2 1B (llama.cpp)
```

---

## Project Structure

```
minimalist-resume/
├── frontend/
│   ├── index.html          # resume website + chat widget
│   └── styles.css          # styling
├── backend/
│   ├── app.py              # FastAPI backend, RAG chain, Excel logger
│   ├── ingest.py           # PDF/HTML/TXT/GitHub → ChromaDB
│   ├── chroma_db/          # vector database (gitignored)
│   └── hr_questions.xlsx   # logged recruiter questions (gitignored)
└── README.md
```

---

## Features

- **Fully offline LLM** — Llama 3.2 1B runs locally on Raspberry Pi, no API costs
- **RAG chatbot** — answers questions based on resume docs, website, and GitHub repos
- **Multilingual** — responds in the same language as the question (EN/DE)
- **HR question logging** — all chatbot questions saved to Excel, downloadable at `/download-questions`
- **Auto-ingestion** — cron job re-ingests docs daily at 3 AM to stay up to date
- **Dark/light mode** — toggle between themes
- **Auto-deploy** — `deploy.sh` pulls from git and copies to nginx web root

---

## Setup

### Prerequisites

- Raspberry Pi 4 (4GB+ RAM recommended)
- Python 3.10+
- llama.cpp built from source
- nginx

### 1. Clone the repo

```bash
git clone https://github.com/stawank/minimalist-resume.git
cd minimalist-resume
```

### 2. Install Python dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Download the model

```bash
~/llama.cpp/build/bin/llama-cli -hf bartowski/Llama-3.2-1B-Instruct-GGUF:Q4_K_M
```

### 4. Add your documents

```bash
mkdir ~/resume_docs
cp /path/to/your/*.pdf ~/resume_docs/
```

### 5. Ingest documents

```bash
python3 ingest.py
```

### 6. Start the backend

```bash
uvicorn app:app --host 127.0.0.1 --port 8000
```

### 7. Configure nginx

```bash
sudo cp /etc/nginx/sites-available/minimalist-resume /etc/nginx/sites-available/minimalist-resume
sudo nginx -t && sudo systemctl reload nginx
```

---

## Daily Startup

Everything starts automatically on boot via systemd:

```bash
sudo systemctl status nginx
sudo systemctl status resume-backend
sudo systemctl status cloudflared
```

To deploy latest changes:

```bash
~/deploy.sh
```

---

## Auto re-ingestion (cron)

Documents are re-ingested every day at 3 AM:

```
0 3 * * * cd /home/stawan/minimalist-resume/backend && /home/stawan/minimalist-resume/backend/venv/bin/python3 ingest.py >> ingest.log 2>&1 && sudo systemctl restart resume-backend
```

---

## Download HR Questions

All questions asked via the chatbot are logged. Download the Excel file at:

```
https://stawank.cv/download-questions
```

---

## License

MIT
## Credits

- Frontend design inspired by [KeelanJon](https://github.com/KeelanJon) — thank you for the clean minimalist aesthetic