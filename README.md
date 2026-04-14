# 🤖 AI Text Summarization Web Application

> A production-ready, full-stack NLP web application that summarizes long text into concise, meaningful summaries using **Extractive (LSA)** and **Abstractive (BART)** methods.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat&logo=flask&logoColor=white)
![HuggingFace](https://img.shields.io/badge/HuggingFace-BART-FFD21E?style=flat&logo=huggingface&logoColor=black)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)
![Deployment](https://img.shields.io/badge/Deploy-Render%20%7C%20Railway-blue?style=flat)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Sample Inputs & Outputs](#sample-inputs--outputs)
- [Deployment](#deployment)
- [Future Improvements](#future-improvements)

---

## 🌟 Overview

This web application leverages state-of-the-art Natural Language Processing to help users quickly extract the most important information from long texts. It supports two distinct summarization paradigms:

| Method | Model | Speed | Description |
|--------|-------|-------|-------------|
| **Extractive** | Sumy LSA | ⚡ Fast | Selects the most important sentences from the original text |
| **Abstractive** | BART (facebook/bart-large-cnn) | 🤖 AI-powered | Generates a brand new, concise summary in its own words |

---

## ✨ Features

### Core
- ✅ **Dual summarization modes** — Extractive (LSA) and Abstractive (BART)
- ✅ **Adjustable summary length** — slider to control output verbosity (10–70%)
- ✅ **File upload support** — accepts `.txt` and `.pdf` files
- ✅ **Speech-to-text input** — dictate text using your microphone (Web Speech API)
- ✅ **Compression statistics** — original vs. summary word count and compression ratio

### UI/UX
- ✅ **Dark/light mode** — persisted in local storage
- ✅ **Drag-and-drop** file upload zone
- ✅ **Live character & word counter** with color warnings
- ✅ **Copy to clipboard** with visual feedback
- ✅ **Download summary** as `.txt` file
- ✅ **Summary history** — last 10 summaries cached in local storage
- ✅ **Loading animations** — spinner and indeterminate progress bar
- ✅ **Toast notifications** for all actions
- ✅ **Fully responsive** — works on mobile, tablet, and desktop

### Technical
- ✅ **Modular Flask architecture** — separate blueprints, utils, and summarizer modules
- ✅ **Model pre-loading** — BART loaded once at startup for fast inference
- ✅ **Chunked processing** — handles texts longer than BART's 1024-token limit
- ✅ **Thread-safe analytics** — in-memory counter with mutex lock
- ✅ **Full error handling** — input validation, edge cases, proper HTTP status codes

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.10+, Flask 3.0, Flask-CORS |
| **Extractive NLP** | Sumy (LSA Algorithm), NLTK |
| **Abstractive NLP** | HuggingFace Transformers, `facebook/bart-large-cnn`, PyTorch |
| **PDF Parsing** | PyMuPDF (fitz) |
| **Encoding Detection** | chardet |
| **Frontend** | HTML5, Vanilla CSS, Vanilla JavaScript |
| **Fonts** | Google Fonts (Inter, Fira Code) |
| **Production Server** | Gunicorn |
| **Deployment** | Render / Railway |

---

## 📁 Project Structure

```
Text Summarization/
├── app.py                    # Flask app factory + entry point
├── requirements.txt          # Python dependencies
├── Procfile                  # Gunicorn deployment command
├── .env.example              # Environment variable template
├── .gitignore
├── README.md
│
├── summarizer/               # NLP summarization engines
│   ├── __init__.py
│   ├── extractive.py         # LSA via Sumy
│   └── abstractive.py        # BART via HuggingFace Transformers
│
├── routes/                   # Flask blueprints
│   ├── __init__.py
│   ├── api.py                # REST API: /api/summarize, /api/upload, /api/analytics
│   └── views.py              # Frontend route: /
│
├── utils/                    # Utility modules
│   ├── __init__.py
│   ├── file_handler.py       # .txt/.pdf text extraction
│   └── analytics.py          # Thread-safe usage stats
│
├── templates/
│   └── index.html            # Main SPA-style template
│
└── static/
    ├── css/
    │   └── style.css         # Full custom CSS (dark/light, glassmorphism)
    └── js/
        └── main.js           # All client-side interactivity
```

---

## ⚙️ Installation

### Prerequisites

- Python **3.10+**
- pip
- (Optional) GPU with CUDA for faster BART inference

### Step-by-Step Setup

**1. Clone the repository**
```bash
git clone https://github.com/yourusername/ai-text-summarizer.git
cd ai-text-summarizer
```

**2. Create and activate a virtual environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Download NLTK data** (required by Sumy)
```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"
```

**5. Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your settings (SECRET_KEY, etc.)
```

**6. Run the application**
```bash
python app.py
```

Open your browser at **http://localhost:5000** 🚀

> **Note:** On first run, the BART model (~1.6 GB) will be downloaded automatically by HuggingFace and cached locally. Subsequent starts will be instant.

---

## 🚀 Usage

### Summarizing Text
1. Paste your text into the **Input Text** box
2. Select a **method**: Extractive (fast) or Abstractive (AI-generated)
3. Adjust the **length slider** (10–70% of original)
4. Click **Summarize**
5. View the summary, stats, and use **Copy** or **Download**

### Uploading a File
1. Drag and drop a `.txt` or `.pdf` file into the upload zone
2. Select your method and length
3. Click **Summarize** — the text will be extracted and summarized

### Speech-to-Text
1. Click the **🎙️ Speak** button in the input card
2. Speak your text — it will appear in the input box
3. Click **Stop** when done, then **Summarize**

---

## 📡 API Reference

### `POST /api/summarize`

Summarize plain text.

**Request Body (JSON):**
```json
{
  "text": "Your long text here...",
  "method": "extractive",
  "length_ratio": 0.3
}
```

**Response:**
```json
{
  "success": true,
  "summary": "Key sentences or generated summary...",
  "stats": {
    "original_words": 450,
    "original_chars": 2800,
    "summary_words": 85,
    "summary_chars": 520,
    "compression_ratio": 81.1,
    "processing_time_ms": 342,
    "method": "extractive"
  }
}
```

---

### `POST /api/upload`

Upload and summarize a `.txt` or `.pdf` file.

**Form Data:**
- `file` — the file to upload
- `method` — `"extractive"` or `"abstractive"`
- `length_ratio` — float between `0.1` and `0.9`

**Response:** Same as `/api/summarize`, plus `extracted_text` (first 5000 chars).

---

### `GET /api/analytics`

Get usage statistics.

**Response:**
```json
{
  "success": true,
  "stats": {
    "total": 42,
    "extractive": 28,
    "abstractive": 14,
    "file_uploads": 5,
    "started_at": "2024-01-01T12:00:00+00:00"
  }
}
```

---

## 📊 Sample Inputs & Outputs

### Sample Input (Extractive)
```
Artificial intelligence (AI) is intelligence demonstrated by machines, 
as opposed to the natural intelligence displayed by animals including humans. 
AI research has been defined as the field of study of intelligent agents, 
which refers to any system that perceives its environment and takes actions 
that maximize its chance of achieving its goals...
```

### Sample Output
```
Artificial intelligence (AI) is intelligence demonstrated by machines, 
as opposed to the natural intelligence displayed by animals including humans. 
AI research has been defined as the field of study of intelligent agents.
```

**Stats:** 180 words → 38 words | **79% compression** | ⚡ 245ms

---

## 🚢 Deployment

### Deploy on Render (Free Tier)

1. Push your project to a GitHub repository
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your repository
4. Set **Build Command**: `pip install -r requirements.txt`
5. Set **Start Command**: `gunicorn app:app --workers 2 --timeout 120`
6. Add environment variable: `SECRET_KEY=your-random-secret`
7. Deploy! 🎉

> **Note:** The first request may take 30–60 seconds on free tier as the BART model loads.

### Deploy on Railway

1. Install Railway CLI: `npm install -g @railway/cli`
2. `railway login && railway init`
3. `railway up`
4. Set `SECRET_KEY` in Railway dashboard → Variables

---

## 🔮 Future Improvements

| Feature | Priority | Notes |
|---------|----------|-------|
| Multi-language summarization | High | Add mBART or mT5 model |
| User authentication | Medium | Flask-Login + SQLite |
| Persistent history (database) | Medium | SQLAlchemy + PostgreSQL |
| Sentence highlighting | Medium | Show which sentences were extracted |
| Batch file summarization | Low | Process multiple files at once |
| Summarization of URLs | Low | Scrape article content via BeautifulSoup |
| Fine-tuned domain models | Low | Medical/Legal/Scientific BART variants |
| Export to PDF/DOCX | Low | reportlab or python-docx |

---

## 📜 License

This project is licensed under the **MIT License** — feel free to use, modify, and distribute.

---

## 🙏 Acknowledgements

- [facebook/bart-large-cnn](https://huggingface.co/facebook/bart-large-cnn) — BART model by Facebook AI
- [Sumy](https://github.com/miso-belica/sumy) — Python library for automatic text summarization
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) — Blazing fast PDF parsing
- [HuggingFace Transformers](https://github.com/huggingface/transformers) — The backbone of modern NLP

---

*Built with ❤️ for portfolio and research purposes.*
