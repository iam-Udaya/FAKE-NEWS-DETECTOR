# Fake News Detector for Students 🔍

An AI-powered news credibility analyzer built with **Python**, **Streamlit**, **Google Gemini 2.5 Flash**, and **MongoDB Atlas**.

---

## ✨ Features

| Feature | Description |
|---|---|
| 📝 Text Analysis | Paste any article text for instant AI analysis |
| 🌐 URL Scraping | Auto-extract content from news website URLs |
| 🤖 Gemini AI | Credibility & confidence scores, verdict, key claims, red flags |
| 📊 Dashboard | Live stats: total analyses, avg score, verdict distribution |
| 📈 Charts | Trend line, pie chart, bar chart via Plotly |
| 📋 History | Search, filter, view full reports, delete records |
| 📥 Export | Download reports as PDF, TXT, or JSON |
| 🗄️ MongoDB | Persistent storage of all analyses in Atlas |

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- MongoDB Atlas account (free tier works)
- Google AI Studio API key

### 2. Clone & Install

```bash
# Navigate to project directory
cd fake-news-detector

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy the template
copy .env.example .env
```

Edit `.env` with your credentials:

```env
GEMINI_API_KEY=your_gemini_api_key_here
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net/
MONGODB_DB_NAME=fake_news_detector
```

#### Get Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click **Create API Key**
3. Copy and paste into `.env`

#### Get MongoDB Atlas URI
1. Go to [MongoDB Atlas](https://cloud.mongodb.com)
2. Create a free cluster (M0 Sandbox)
3. Click **Connect → Connect your application**
4. Copy the connection string
5. Replace `<password>` with your DB user password
6. Add your IP to the **Network Access** allowlist (or use `0.0.0.0/0` for development)

### 4. Run the App

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 📁 Project Structure

```
fake-news-detector/
│
├── app.py              # Main Streamlit UI (Analyze page)
├── config.py           # Centralized configuration
├── database.py         # MongoDB connection & CRUD
├── analyzer.py         # Core analysis orchestrator
├── scraper.py          # URL article extraction
├── utils.py            # Charts, export helpers
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
│
├── pages/
│   └── History.py      # History & Dashboard page
│
└── services/
    ├── gemini_service.py   # Google Gemini AI wrapper
    └── mongo_service.py    # High-level MongoDB service
```

---

## 🗄️ MongoDB Schema

**Database:** `fake_news_detector`  
**Collection:** `analyses`

```json
{
  "_id": "ObjectId",
  "article_title": "string",
  "article_text": "string (first 5000 chars)",
  "source_url": "string",
  "credibility_score": 0,
  "confidence_score": 0,
  "verdict": "Likely Real | Suspicious | Likely Fake",
  "summary": "string",
  "analysis": {
    "detailed_explanation": "string",
    "key_claims": ["..."],
    "red_flags": ["..."],
    "trust_indicators": ["..."],
    "fact_checking_suggestions": ["..."],
    "bias_indicators": "string",
    "emotional_language_score": 0,
    "source_credibility_notes": "string",
    "missing_context": "string"
  },
  "created_at": "ISO 8601 timestamp"
}
```

---

## 🧠 AI Analysis Output

For each article, Gemini 2.5 Flash generates:

| Field | Range | Meaning |
|---|---|---|
| `credibility_score` | 0–100 | Overall trustworthiness |
| `confidence_score` | 0–100 | AI's confidence in the verdict |
| `verdict` | 3 values | Likely Real / Suspicious / Likely Fake |
| `emotional_language_score` | 0–10 | Sensationalism level |

**Verdict Thresholds:**
- ✅ **Likely Real**: score ≥ 70
- ⚠️ **Suspicious**: score 40–69
- ❌ **Likely Fake**: score < 40

---

## 🛠 Troubleshooting

| Problem | Solution |
|---|---|
| `GEMINI_API_KEY missing` | Add key to `.env` file |
| `MongoDB connection failed` | Check URI, whitelist your IP in Atlas |
| URL scraping fails | Site may be behind paywall/JS — use text input instead |
| `newspaper3k` import error | Run `pip install newspaper3k` separately |
| PDF export fails | Run `pip install reportlab` |

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `streamlit` | Web UI framework |
| `google-generativeai` | Gemini AI API |
| `pymongo` | MongoDB driver |
| `newspaper3k` | Article extraction |
| `beautifulsoup4` | HTML parsing fallback |
| `plotly` | Interactive charts |
| `reportlab` | PDF generation |
| `python-dotenv` | Environment management |

---

## 🎓 Educational Use

This tool is designed to help students:
- Identify misleading headlines and emotional language
- Understand what makes a source credible
- Practice fact-checking with AI guidance
- Build media literacy skills

---

## 📄 License

MIT License – Free for educational use.

---

*Powered by Google Gemini 2.5 Flash · MongoDB Atlas · Streamlit*
