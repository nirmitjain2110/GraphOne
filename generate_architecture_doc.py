"""
Generates the architecture.pdf design document required for Phase VI submission.
"""

import os
from fpdf import FPDF


class ArchitecturePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "GraphOne / FrontierAtlas - Technical Architecture & Scale Design", new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", "I", 9)
        self.cell(0, 5, "Production Design for 500,000+ Multi-Dimensional Intelligence Graph Ingestion", new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()} / {{nb}}", align="C")

    def section_title(self, title):
        self.set_font("Helvetica", "B", 12)
        self.set_fill_color(230, 240, 250)
        self.cell(0, 8, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def sub_title(self, title):
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 6, title, new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body_text(self, text):
        self.set_font("Helvetica", "", 9.5)
        self.multi_cell(0, 5, text)
        self.ln(3)


def create_pdf(filename="architecture.pdf"):
    pdf = ArchitecturePDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    # Title & Executive Summary
    pdf.body_text(
        "Executive Summary: This document details the production engineering architecture for GraphOne's global AI Intelligence Graph. "
        "The system is designed to continuously ingest, normalize, resolve, and link hundreds of thousands (500k+) of entity records "
        "across startups, products, research papers, real-time news signals, and job openings with high fault tolerance."
    )

    # 1. Scale Strategy (500,000+ Records)
    pdf.section_title("1. Scale Strategy: Acquiring 500,000+ Entities")
    pdf.body_text(
        "To scale data acquisition to 500,000+ startups, products, and papers without manual intervention, the architecture transitions "
        "from a single async process to a Distributed Micro-Crawler Mesh:\n"
        "- Distributed Event Backbone: Apache Kafka / RabbitMQ partition queues by domain tier (High-frequency news vs. Bulk directory scraping).\n"
        "- Headless Crawler Swarm: Auto-scaling Kubernetes pods running Playwright Async and Scrapy clusters. IP rotation managed via residential proxy pools (BrightData/ScraperAPI) to bypass Cloudflare/DataDome captchas.\n"
        "- Partitioned Ingestion: Partitioning by domain shards & seed directories ensures parallel workers crawl distinct namespace segments with zero lock contention."
    )

    # 2. Handling HTTP 413s & 429s
    pdf.section_title("2. Managing Context Windows (413) & Rate Limits (429)")
    pdf.body_text(
        "Extracting structured JSON from massive web pages via LLMs requires strict context-window and rate-limit guardrails:\n"
        "- 413 Payload Too Large Mitigation: Raw HTML DOMs are passed through an AST-based DOM Cleaner (stripping script/style tags, inline SVG, boilerplates) "
        "followed by a Semantic Token Slicer. Payload chunk sizes are clamped below model token limits (e.g. 12,000 chars) while preserving dense headers/content.\n"
        "- 429 Rate Limit Mitigation: Implements a Leaky Bucket Rate Limiter combined with an Exponential Backoff + Jitter retry loop (delay = 2^attempt + U(0, 1.5)s).\n"
        "- Multi-Tier Provider Fallback Mesh: If primary LLM (Gemini Flash) hits quota limits, traffic fails over seamlessly to Groq (Llama 3.1 70B), then OpenAI GPT-4o-mini, and finally a local heuristic parser."
    )

    pdf.add_page()

    # 3. Freshness Tracking & Deduplication Across Distributed Nodes
    pdf.section_title("3. Freshness Tracking & Distributed Deduplication")
    pdf.body_text(
        "Ensuring real-time news and job postings are strictly < 24-hours fresh and processed exactly once across distributed crawler nodes:\n"
        "- Distributed Redis Bloom Filters: Before fetching full page payloads, crawler nodes check a centralized Redis Bloom Filter keyed by normalized canonical URL hash (URL-hash + PubDate). Bloom filters provide O(1) time complexity with 99.9% memory efficiency.\n"
        "- 24-Hour Sliding TTL: Deduplication keys are assigned a strict 24-hour Sliding Time-To-Live (TTL), guaranteeing that content is checked afresh daily while preventing duplicate work across parallel crawler instances.\n"
        "- Publication Timestamp Normalization: Extracted publication dates (including relative formats like '3 hours ago') are parsed into standard UTC ISO-8601 timestamps and filtered out if delta > 24 hours."
    )

    # 4. Storage Strategy
    pdf.section_title("4. Multi-Modal Storage Architecture")
    pdf.body_text(
        "GraphOne requires storing rich entity schemas alongside deep relational links and semantic vector embeddings:\n"
        "- Primary RDBMS (PostgreSQL 16 + JSONB): Stores core entity metadata (Startups, Products, Papers, Jobs, News) with ACID compliance, schema versioning ('1.0'), and fast B-Tree indexing on canonical entity IDs.\n"
        "- Vector Store (Qdrant / Pinecone): Stores dense semantic vector embeddings for research paper abstracts, product descriptions, and news content to enable RAG and similarity search.\n"
        "- Graph Database (Neo4j / Memgraph): Maps complex graph relationships: (Startup)-[:BUILD_PRODUCT]->(Product), (Paper)-[:CORRELATED_WITH]->(GitHub_Repo), (Company)-[:POSTED_JOB]->(Job). Enables topological traversal for intelligence insights."
    )

    # 5. Entity Resolution Pipeline
    pdf.section_title("5. Dynamic Entity Canonicalization & Resolution")
    pdf.body_text(
        "Messy raw entity strings (e.g. 'Open AI', 'OpenAI Inc.', 'OpenAI') are normalized using a hybrid approach:\n"
        "1. Token Normalization: Legal suffix removal ('Inc', 'LLC', 'Corp') and string cleaning.\n"
        "2. Exact Alias Matching: O(1) dictionary lookup against alias maps.\n"
        "3. RapidFuzz Similarity: Token sort ratio matching against a 50-entity seed canonical database (threshold >= 82%).\n"
        "4. Audit Logging: Every mapping event is recorded in entity_mapping_log.csv for transparent lineage tracking."
    )

    pdf.output(filename)
    print(f"Successfully generated {filename}")


if __name__ == "__main__":
    create_pdf()
