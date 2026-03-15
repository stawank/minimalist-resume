# minimalist-resume

A personal resume website self-hosted on a Raspberry Pi with a terminal/hacker aesthetic and an AI-powered chatbot. Hiring managers can ask questions about experience, skills, and projects directly on the site.

**Live:** [stawank.cv](https://stawank.cv)

---

## What makes it different

- **Boot sequence** — systemd-style `[OK]` / `[WARN]` lines on every page load
- **Live uptime ticker** — `stawan@pi4 ~ $ uptime` ticking in real time in the header
- **AI chatbot** — RAG over resume docs, website, and GitHub using Claude API + ChromaDB
- **Streaming responses** — tokens stream word by word via SSE
- **JSON-driven content** — all text lives in `en.json` / `de.json`, zero HTML edits needed for content changes
- **Bilingual** — full EN/DE support, chatbot responds in the language of the question
- **Terminal aesthetic** — JetBrains Mono, phosphor green, scanlines, dark mode by default

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
  ├── /              → serves static frontend (index.html + en.json + de.json)
  └── /chat/stream   → proxies to FastAPI (port 8000)
                          │
                          ├── ChromaDB (vector search)
                          │     └── resume docs + website + GitHub
                          │
                          └── Claude API (streaming)
```

---

## Project Structure

```
minimalist-resume/
├── frontend/
│   ├── index.html      # shell — all content rendered from JSON
│   ├── styles.css      # terminal aesthetic
│   ├── en.json         # all English content (edit this to update the site)
│   └── de.json         # all German content
├── backend/
│   ├── app.py          # FastAPI backend, RAG chain, Excel logger
│   ├── ingest.py       # PDF/HTML/TXT/GitHub → ChromaDB
│   ├── .env.example    # environment variable template
│   ├── chroma_db/      # vector database (gitignored)
│   └── hr_questions.xlsx  # logged questions (gitignored)
└── README.md
```

---

## Updating content

All resume content lives in `frontend/en.json` and `frontend/de.json`. To make any change:

```bash
nano frontend/en.json   # edit whatever you need
~/deploy.sh             # deploy
```

JSON structure:
```
sections    → section title labels
header      → name, title, location, uptime, contact links
about       → role / stack / exp / currently lines
experience  → array of jobs with title, company, period, bullets[]
projects    → array of projects with title, stack, description, links[]
skills      → array of groups with group label and items[]
education   → array of degrees with degree, school, period, description, links[]
chatbot     → toggle label, header title, placeholder, footer text
boot        → boot sequence lines[] and prompt string
```

---

## Features

- **Terminal boot sequence** — customisable lines in `boot.lines` in the JSON
- **Live uptime** — real-time clock ticking from page load
- **AI chatbot** — Claude API with RAG answers recruiter questions
- **Streaming** — SSE word-by-word token streaming
- **Bilingual** — EN/DE toggle, chatbot responds in question language
- **HR question logging** — all questions saved to Excel
- **Visitor logging** — logs IPs and timestamps
- **Response caching** — repeated questions served from cache
- **Auto-ingestion** — cron re-ingests docs daily at 3 AM
- **Dark mode by default** — light mode toggle available
- **Auto-deploy** — `deploy.sh` pulls from git and copies to Nginx web root

---

## Setup

### Prerequisites

- Raspberry Pi 4 (4GB+ RAM recommended)
- Python 3.10+
- Nginx
- Anthropic API key — [console.anthropic.com](https://console.anthropic.com)

### 1. Clone

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

### 7. Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/minimalist-resume
sudo nginx -t && sudo systemctl reload nginx
```

---

## Deploy script

`deploy.sh` pulls the latest code from git and copies the frontend to the Nginx web root. Create it once on the Pi:

```bash
nano ~/deploy.sh
```

Paste this:

```bash
#!/bin/bash
set -e

cd ~/minimalist-resume
git pull origin main

cp frontend/index.html /var/www/html/
cp frontend/styles.css  /var/www/html/
cp frontend/en.json     /var/www/html/
cp frontend/de.json     /var/www/html/

sudo systemctl restart resume-backend
echo "[OK] deployed"
```

Make it executable:

```bash
chmod +x ~/deploy.sh
```

Then deploy any time with:

```bash
~/deploy.sh
```

> Adjust `/var/www/html/` to match your Nginx root if it differs.

---

## Running as a service

Backend starts automatically on boot via systemd:

```bash
sudo systemctl status nginx
sudo systemctl status resume-backend
```

Deploy latest changes:

```bash
~/deploy.sh
```

---

## Auto re-ingestion

Documents re-ingested daily at 3 AM:

```
0 3 * * * cd $HOME/minimalist-resume/backend && ./venv/bin/python3 ingest.py >> ingest.log 2>&1 && sudo systemctl restart resume-backend
```

---

## Download logged questions

```
https://stawank.cv/download-questions
```

---

## License

MIT