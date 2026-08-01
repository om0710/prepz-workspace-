---
title: Prepz AI Workspace
emoji: 📚
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# 📚 Prepz AI Workspace - Engineering Study & RAG Platform

> **AI-Powered Engineering Study Assistant with Multi-Format RAG Search, Automated PYQ Paper Generation, and In-Browser Document Reader.**

---

## ✨ Key Features

- **📄 Multi-Format RAG Engine (`.pdf`, `.docx`, `.doc`)**:
  - Ingest, chunk, and search engineering notes, tutorial sheets, and past year question papers (PYQs).
  - Native text & table extraction for Word documents and PDFs into ChromaDB vector storage.

- **🔒 Private Library vs. 🌐 Shared Community Catalog**:
  - **My Documents**: Keep your personal assignments, resumes, and private notes private to your account.
  - **Shared Catalog**: Browse, search, and download public study materials contributed by engineering students.

- **📝 Custom In-Browser Document Reader**:
  - View Word documents (`.docx`, `.doc`) inline inside the browser with formatted typography, tables, and quick download links without needing Microsoft Word installed.

- **🎯 AI Exam Paper & PYQ Generator**:
  - Automatically analyzes uploaded PYQs for any subject & semester to generate predicted exam question papers with frequency analysis and probability scores.

- **💬 LangGraph Multi-Turn Agentic Chat**:
  - Powered by Groq `llama-3.3-70b-versatile` with fallbacks, hybrid vector + BM25 search routing, and full conversation thread persistence.

- **🔥 Gamified Learning & Contribution Score**:
  - Tracks student study streaks, awards contribution points for uploads, and maintains a community leaderboard.

---

## 🛠️ Tech Stack

- **Backend Framework**: FastAPI (Python 3.10+)
- **AI / LLM**: Groq API (`llama-3.3-70b-versatile`)
- **Agent Orchestration**: LangGraph, LangChain, LangChain-Core
- **Vector Database**: ChromaDB + HuggingFace Embeddings (`all-mpnet-base-v2`)
- **Keyword Search**: Rank-BM25 (Hybrid Dense + Sparse Retrieval)
- **Database**: SQLite3 (WAL Write-Ahead Logging Mode for concurrency)
- **Frontend**: Vanilla HTML5, CSS3, JavaScript (ES6+), Google Fonts (Plus Jakarta Sans)

---

## 📂 Project Structure

```text
.
├── app.py                 # Primary FastAPI Web Server & API Endpoints
├── backend_rag.py         # LangGraph Chat Workflow & Tool Routing Engine
├── rag.py                 # Multi-Format Text Extraction & Vector Store Ingestion
├── database.py            # SQLite User Profiles, Upload Metadata & Thread Storage
├── tools.py               # Auxiliary AI Tools (Calculator, Wikipedia Search, Time)
├── static/                # Frontend UI Assets
│   ├── index.html         # Main Workspace & Documents Web Interface
│   ├── style.css          # Modern Glassmorphic CSS Styling & Design System
│   └── app.js             # Interactive SPA Logic & Real-time Streaming Handler
├── uploads/               # Local Storage Directory for Uploaded Documents
├── Dockerfile             # Docker Container Configuration
├── Procfile               # Render / Railway Deployment Procfile
├── requirements.txt       # Python Package Dependencies
└── README.md              # Project Documentation
```

---

## ⚙️ Local Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/om0710/prepz-workspace-.git
cd prepz-workspace-
```

### 2. Create and Activate Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate        # On Mac / Linux
# venv\Scripts\activate          # On Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_api_key_here
```

### 5. Run the Server
```bash
python app.py
```
Open your browser and navigate to **`http://localhost:7865`**.

---

## ☁️ Deployment Guide

### Deploying to Render.com

1. Create a **New Web Service** on [Render.com](https://render.com).
2. Connect your GitHub repository `om0710/prepz-workspace-`.
3. Set the following build options:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. Add Environment Variable: `GROQ_API_KEY` = *your API key*.
5. Click **Create Web Service**.

---

## 👨‍💻 Author

**Om Bansal**  
- GitHub: [@om0710](https://github.com/om0710)  
- LinkedIn: [Om Bansal](https://www.linkedin.com/in/om-bansal-78420430a/)
