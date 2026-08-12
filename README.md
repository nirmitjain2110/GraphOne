# GraphOne AI Ingestion & Deterministic Entity Resolution Pipeline

Production-grade asynchronous data pipeline built for **GraphOne / FrontierAtlas**. Ingests, cleans, extracts, normalizes, and canonicalizes multi-dimensional data across AI Startups, Products, Research Papers (with GitHub metrics), News, and Jobs.

---

##  Key Capabilities

1. **Massive Bulk Data Acquisition (Phase I)**:
   - **1,000+ AI Startups**: Ingested with metadata (employee count, domain, description).
   - **1,000+ AI Products**: Ingested with pricing models (`FREE`, `FREEMIUM`, `PAID`, `ENTERPRISE`).
   - **1,000+ AI Research Papers**: Bulk fetched from arXiv & PapersWithCode, correlated with associated GitHub repositories and live star counts.
2. **High-Fidelity Signal Crawling with 24-Hour Freshness (Phase II)**:
   - Continuously monitors 5 distinct AI news sources & 5 job boards.
   - Enforces a strict $< 24\text{-hour}$ publication freshness filter with date normalizers (handling relative timestamps like `"2 hours ago"` and missing meta tags).
3. **Resilient Multi-Tier LLM Engine (Phase III)**:
   - Provider Fallback Mesh: `Gemini Flash` $\rightarrow$ `Groq (Llama 3)` $\rightarrow$ `OpenAI (GPT-4o-mini)` $\rightarrow$ `Heuristic Parser`.
   - **Intelligent DOM Chunker**: Cleans HTML noise and slices text payloads to prevent **HTTP 413 (Payload Too Large)**.
   - **Exponential Backoff & Jitter**: Recovers automatically from **HTTP 429 (Too Many Requests)**.
4. **Deterministic Entity Resolution (Phase IV)**:
   - Canonicalizes messy variant strings (e.g. `"Open AI"`, `"OpenAI, Inc."`, `"OpenAI"`) against a seed list of 50 canonical AI organizations.
   - Generates full transparent audit log mapping entries (`entity_mapping_log.csv`).
5. **Production Architecture Design (Phase V & VI)**:
   - Includes `architecture.pdf` detailing scale to $500,000+$ entities, distributed Redis Bloom filter deduplication, and multi-modal database storage strategy.

---

##  Repository Structure

```
├── main.py                         # Main execution pipeline entrypoint
├── generate_architecture_doc.py    # Script to build architecture.pdf
├── architecture.pdf                # Phase VI Architecture & Production Design document
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment template for API keys
├── src/
│   ├── crawlers/
│   │   ├── utils.py                # Stealth headers, HTTP fetcher, date normalizer & 24h filter
│   │   ├── papers_crawler.py       # arXiv API scraper + GitHub star fetcher (1000+ papers)
│   │   ├── startups_crawler.py     # AI startups bulk crawler (1000+ startups)
│   │   ├── products_crawler.py     # AI products crawler + pricing tier classifier (1000+ products)
│   │   ├── news_crawler.py         # 5 AI news sources crawler (<24h freshness)
│   │   └── jobs_crawler.py         # 5 AI job boards crawler (<24h freshness)
│   ├── llm/
│   │   ├── schemas.py              # Canonical Pydantic schemas (Startup, Product, Paper, Job, News)
│   │   ├── chunker.py              # HTML DOM cleaner & payload chunker (Prevents 413)
│   │   └── orchestrator.py         # Resilient multi-tier LLM extraction engine (Prevents 429)
│   ├── resolver/
│   │   └── entity_resolver.py      # Fuzzy matcher & canonical entity mapping engine
│   └── exporters/
│       └── csv_exporter.py         # Exporter for 6 Google Sheets deliverable CSV tabs
├── output/                         # Generated CSV deliverables directory
│   ├── startups.csv                # Tab 1: 1,000+ Startups
│   ├── products.csv                # Tab 2: 1,000+ Products
│   ├── research_papers.csv         # Tab 3: 1,000+ Papers with GitHub metrics
│   ├── jobs.csv                    # Tab 4: 24-hr Fresh Jobs
│   ├── news.csv                    # Tab 5: 24-hr Fresh News
│   └── entity_mapping_log.csv      # Tab 6: Raw vs Canonical mapping log
└── tests/
    └── test_pipeline.py            # Automated Pytest suite
```

---

##  Quickstart Setup & Execution

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
Copy `.env.example` to `.env` and add API keys if LLM extraction is desired (The system automatically falls back gracefully if keys are absent):
```bash
cp .env.example .env
```

### 3. Run Pipeline
To execute bulk scraping, 24-hr signal crawling, entity resolution, and generate all 6 CSV outputs:
```bash
python main.py
```

### 4. Generate Architecture PDF
To compile the `architecture.pdf` design document:
```bash
python generate_architecture_doc.py
```

### 5. Run Test Suite
```bash
pytest tests/
```

---

##  Deliverables Checklist

- [x] **Tab 1: Startups** ($\ge 1,000$ rows) -> `output/startups.csv`
- [x] **Tab 2: Products** ($\ge 1,000$ rows) -> `output/products.csv`
- [x] **Tab 3: Research Papers** ($\ge 1,000$ rows, with GitHub stars) -> `output/research_papers.csv`
- [x] **Tab 4: Jobs** (All 24-hr fresh jobs found across 5 boards) -> `output/jobs.csv`
- [x] **Tab 5: News** (All 24-hr fresh news found across 5 feeds) -> `output/news.csv`
- [x] **Tab 6: Entity Mapping Log** (Raw vs. Canonical names) -> `output/entity_mapping_log.csv`
- [x] **`README.md`**: Complete setup instructions and architecture breakdown.
- [x] **`architecture.pdf`**: Detailed 500k+ scale technical design document.
