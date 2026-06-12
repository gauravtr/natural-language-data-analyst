# 📊 BI Copilot — Ask Your Data Anything

> **Turn any dataset into insights using plain English — no SQL required.**
> Upload a CSV, ask a question, get a chart and a plain-English answer in seconds.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white"/>
  <img src="https://img.shields.io/badge/DuckDB-FFF000?style=for-the-badge&logo=duckdb&logoColor=black"/>
  <img src="https://img.shields.io/badge/Groq-LLaMA_3.3-F54A00?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge"/>
</p>

---

## 🎬 Demo

> **Upload any CSV → type a question → get a chart**

<!-- Replace the line below with your actual screenshot/GIF after recording one -->
<!-- Recommended: use ShareX (Windows) or Kap (Mac) to record a 30-second GIF -->

![Demo](assets/demo.gif)

> *Sample questions that work out of the box on any sales/retail dataset:*
> - "Which product had the highest revenue last quarter?"
> - "Show me monthly sales trend for 2023"
> - "Which region has the lowest average order value?"

---

## 🚀 What Makes This Different

Most "LLM + SQL" projects are demos that break in production. This one is engineered to work reliably:

| Challenge | How it's solved |
|---|---|
| LLM hallucinates column names | Schema injected into every prompt; sqlglot validates output before execution |
| SQL fails at runtime | Self-healing retry loop — error sent back to LLM, fixed automatically (up to 3 attempts) |
| API quota exhausted | 4-model fallback chain (Groq → Gemini); auto-rotates on quota errors |
| High API cost per query | 5 calls → 1 call per query; persistent SQL cache → 0 calls for repeated questions |
| Works only on one dataset | Accepts any CSV / Excel / JSON; each file becomes a queryable DuckDB table |
| No way to measure quality | Built-in evaluation framework; reports execution accuracy + result accuracy |

---

## ✨ Features

- 🗣️ **Natural language to SQL** — powered by Llama 3.3-70B via Groq (free tier)
- 📁 **Universal dataset support** — upload CSV, Excel (.xlsx), JSON, or TSV; ask questions instantly
- 🔄 **Self-healing SQL** — broken queries auto-fix using the runtime error as feedback
- 💾 **Persistent SQL cache** — repeated questions served from disk with zero API calls
- 🤖 **4-model fallback chain** — Groq (primary) → Gemini (backup); auto-rotates on quota errors
- 📈 **Auto chart selection** — rule-based engine picks line / bar / scatter / pie based on result shape
- 🔗 **Multi-table support** — upload multiple files, ask cross-table join questions
- 🧠 **Conversation memory** — follow-up questions reference prior queries automatically
- 📊 **Evaluation framework** — run `eval.py` to measure accuracy on 15 test questions
- 🛡️ **SQL safety layer** — blocks all destructive statements (DROP, DELETE, etc.) before execution

---

## 🏗️ Architecture

```
User types a question
        │
        ▼
 ┌─────────────┐
 │  SQL Cache  │──── Hit? ──────────────────────────────────┐
 │  (disk)     │                                            │
 └─────────────┘                                            │
        │ Miss                                              │
        ▼                                                   │
 ┌─────────────────────────────────────────────────┐        │
 │  Schema Retriever                               │        │
 │  Compact serialization — only relevant tables  │        │
 └─────────────────────────────────────────────────┘        │
        │                                                   │
        ▼                                                   │
 ┌─────────────────────────────────────────────────┐        │
 │  LLM  (1 API call)                              │        │
 │  Groq / Llama 3.3-70B  →  raw SQL               │        │
 │  Gemini fallback if Groq quota exhausted        │        │
 └─────────────────────────────────────────────────┘        │
        │                                                   │
        ▼                                                   │
 ┌─────────────────────────────────────────────────┐        │
 │  SQL Validator  (local — zero API)              │        │
 │  sqlglot parse + safety keyword check           │        │
 └─────────────────────────────────────────────────┘        │
        │                                                   │
        ▼                                                   │
 ┌─────────────────────────────────────────────────┐        │
 │  DuckDB Executor + Self-Healing Loop            │        │
 │  On failure: error → LLM → fixed SQL → retry   │        │
 └─────────────────────────────────────────────────┘        │
        │                                                   │
        ▼                                                   ▼
 ┌───────────────────────┐                    ┌────────────────────┐
 │  Chart Auto-Selector  │                    │   Result from      │
 │  (rule-based, 0 API)  │                    │   cache — instant  │
 └───────────────────────┘                    └────────────────────┘
        │
        ▼
 ┌───────────────────────┐
 │  Local Explainer      │
 │  Template-based,      │
 │  0 API tokens         │
 └───────────────────────┘
        │
        ▼
  Chart + Explanation
  shown to user
```

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|---|---|---|
| LLM (primary) | Groq / Llama 3.3-70B | 14,400 free requests/day — 10× more than Gemini |
| LLM (fallback) | Google Gemini | Automatic failover if Groq quota exhausted |
| SQL Engine | DuckDB | In-process, no server, reads CSV/Parquet natively |
| SQL Validation | sqlglot | Parse + dialect-check before execution |
| Frontend | Streamlit | Chat UI, file uploader, sidebar management |
| Charts | Plotly Express | Interactive line / bar / scatter / pie |
| Data layer | Pandas | File reading, type inference, DataFrame operations |
| Config | python-dotenv | Secure API key loading from `.env` |

---

## ⚡ Quickstart

### Prerequisites
- Python 3.10 or higher
- A free Groq API key from [console.groq.com](https://console.groq.com)

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/bi-copilot.git
cd bi-copilot
```

### 2. Create and activate a virtual environment
```bash
# Mac / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up your API keys
```bash
cp .env.example .env
```
Open `.env` and add your keys:
```env
GROQ_API_KEY=gsk_your_groq_key_here
GEMINI_API_KEY=AIza_your_gemini_key_here   # optional fallback
DB_PATH=bi_copilot.duckdb
```

> **Get a free Groq key:** [console.groq.com](https://console.groq.com) → API Keys → Create API Key
> **Get a free Gemini key:** [aistudio.google.com](https://aistudio.google.com) → Get API Key

### 5. Load the demo dataset (optional)
```bash
python setup_db.py
```
Creates a sample e-commerce database with ~800 orders across 6 tables.

### 6. Launch the app
```bash
streamlit run app.py
```
Opens at **http://localhost:8501**

---

## 🗂️ Using Your Own Data

1. Launch the app
2. Click **"Upload CSV, Excel, or JSON"** in the sidebar
3. Upload your file(s) — each becomes a queryable table
4. The system auto-generates 5 starter questions for your specific dataset
5. Ask anything in the chat input

**Multi-table support:** Upload multiple files to ask cross-table questions like *"Which customers from the users table haven't placed any orders from the orders table?"*

---

## 💬 Example Queries

| Query | What it demonstrates |
|---|---|
| `Which product category had the highest revenue last year?` | Multi-table JOIN + aggregation + date filter |
| `Show me monthly sales trend for 2023` | Time-series → auto line chart |
| `Which customers haven't ordered in 90 days?` | Subquery + date arithmetic |
| `What is the average order value by country?` | GROUP BY + AVG + sorting |
| `Now show only the top 5` | Multi-turn follow-up (references previous query) |

---

## 📐 Project Structure

```
bi-copilot/
│
├── bi_copilot.py       # Core pipeline: schema retrieval, SQL gen, cache,
│                       #   self-healing executor, chart selector, explainer
│
├── app.py              # Streamlit UI: file upload, chat, data preview,
│                       #   sidebar management, chart rendering
│
├── setup_db.py         # Generates sample e-commerce DuckDB database
│                       #   (~800 orders, 6 tables, 2022-2024 data)
│
├── eval.py             # Evaluation framework: runs 15 test questions,
│                       #   reports execution accuracy + result accuracy
│
├── glossary.yaml       # Business metric definitions
│                       #   e.g. revenue = SUM(price * qty * (1-discount))
│
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
└── README.md
```

---

## 📊 Evaluation Results

Run the evaluation suite yourself:
```bash
python eval.py
```

The framework tests 15 business questions with automated correctness checks:

| Metric | Description |
|---|---|
| **Execution accuracy** | % of questions where SQL ran without error |
| **Result accuracy** | % of questions where the answer was correct |
| **Avg latency** | Seconds per query end-to-end |

> Results vary by LLM model and dataset. Typical free-tier performance: **80–90% execution accuracy**, **65–75% result accuracy**.

---

## 🧠 Key Engineering Decisions

**Why 1 API call instead of 3?**
The naive implementation runs three sequential calls: ambiguity check → SQL generation → result explanation. By combining these into a single prompt and generating explanations locally from the DataFrame, the per-query API cost drops by ~80%. This makes the project usable within free-tier limits during development.

**Why a persistent SQL cache?**
In a demo setting, the same questions get asked repeatedly. Caching successful SQL to disk means that after the first run, every repeated question returns instantly with zero API calls — critical for interview demos where reliability matters more than anything.

**Why Groq over Gemini as primary?**
Groq's free tier gives 14,400 requests/day vs Gemini's ~1,500. For a development project with an evaluation framework running 15+ queries, Gemini's limits are exhausted within hours. Groq gives roughly the same generation quality for SQL tasks with 10× more headroom.

**Why DuckDB over SQLite or PostgreSQL?**
DuckDB runs entirely in-process (no server to spin up), reads CSV and Parquet files natively, and handles analytical queries (GROUP BY, window functions, DATE_TRUNC) significantly faster than SQLite. For a demo that needs to load any uploaded file and query it instantly, it's the right tool.

---

## 🗺️ Roadmap

- [ ] Voice input (Whisper API for speech-to-SQL)
- [ ] Export results as PDF report
- [ ] Schema relationship detection (auto-suggest JOINs)
- [ ] Slack / Teams bot integration
- [ ] Support for database connections (PostgreSQL, MySQL, Snowflake)
- [ ] Expanded evaluation set (50+ questions)

---

## 🤝 Contributing

Pull requests are welcome. For major changes, open an issue first to discuss what you'd like to change.

---

## 📄 License

[MIT](LICENSE)

---

## 👤 Author

**Gaurav Tripathi**
- GitHub: [@YOUR_USERNAME](https://github.com/YOUR_USERNAME)
- LinkedIn: [linkedin.com/in/YOUR_PROFILE](https://www.linkedin.com/in/gaurav-tripathi-a43656284/)

---

<p align="center">
  <i>Built as a placement project to demonstrate end-to-end LLM application development.</i><br/>
  <i>If this helped you, consider giving it a ⭐</i>
</p>
