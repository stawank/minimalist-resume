# Minimalist Resume Website with AI Chatbot

A personal resume website served from a Raspberry Pi with an AI-powered chatbot. Recruiters can ask questions about my experience, skills, and projects directly on the site.

**Live:** [stawank.cv](https://https://raspberrypi.tail1b2b1f.ts.net/)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, Vanilla JS |
| Web Server | Nginx |
| Backend | FastAPI (Python) |
| LLM | Claude API (Anthropic) |
| RAG | LangChain + ChromaDB |
| Embeddings | BAAI/bge-small-en-v1.5 |
| Tunnel | Tailscale Funnel |
| Hardware | Raspberry Pi 4 |

---

## Architecture

```
Visitor
  │
  ▼
Tailscale Funnel (bypasses CG-NAT)
  │
  ▼
Nginx (port 80)
  ├── /              → serves static frontend
  └── /chat/stream   → proxies to FastAPI (port 8000)
                          │
                          ├── ChromaDB (vector search)
                          │     └── resume docs + website + GitHub
                          │
                          └── Claude API
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
│   ├── .env.example        # environment variable template
│   ├── chroma_db/          # vector database (gitignored)
│   └── hr_questions.xlsx   # logged recruiter questions (gitignored)
└── README.md
```

---

## Features

- **AI chatbot** — answers recruiter questions using RAG over resume docs, website, and GitHub
- **Streaming responses** — tokens stream word by word for fast UX
- **Multilingual** — responds in the same language as the question (EN/DE)
- **HR question logging** — all questions saved to Excel, downloadable at `/download-questions`
- **Visitor logging** — logs visitor IPs and timestamps
- **Response caching** — repeated questions served instantly from cache
- **Auto-ingestion** — cron job re-ingests docs daily to stay up to date
- **Dark/light mode** — toggle between themes
- **Auto-deploy** — `deploy.sh` pulls from git and copies to nginx web root

---

## Setup

### Prerequisites

- Raspberry Pi 4 (4GB+ RAM recommended)
- Python 3.10+
- Nginx
- Anthropic API key (get one at [console.anthropic.com](https://console.anthropic.com))

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

### 3. Configure environment variables

```bash
cp backend/.env.example backend/.env
nano backend/.env
```

Fill in your values:

```env
DB_PATH=$HOME/minimalist-resume/backend/chroma_db
LOG_PATH=$HOME/minimalist-resume/backend/hr_questions.xlsx
VISITOR_LOG=$HOME/minimalist-resume/backend/visitors.xlsx
ANTHROPIC_API_KEY=your_key_here
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

Copy the nginx config and reload:

```bash
sudo nano /etc/nginx/sites-available/minimalist-resume
sudo nginx -t && sudo systemctl reload nginx
```

---

## Running as a Service

The backend runs automatically on boot via systemd:

```bash
sudo systemctl status nginx
sudo systemctl status resume-backend
```

To deploy latest changes:

```bash
~/deploy.sh
```

---

## Auto re-ingestion (cron)

Documents are re-ingested every day at 3 AM:

```
0 3 * * * cd $HOME/minimalist-resume/backend && ./venv/bin/python3 ingest.py >> ingest.log 2>&1 && sudo systemctl restart resume-backend
```

---

## Download HR Questions

All questions asked via the chatbot are logged. Download the Excel file at:

```
https://stawank.cv/download-questions
```

---

## Credits

- Frontend design inspired by [KeelanJon](https://github.com/KeelanJon) — thank you for the clean minimalist aesthetic

---

## License

MIT