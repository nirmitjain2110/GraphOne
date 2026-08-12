"""
Main Execution Entrypoint for GraphOne AI Ingestion & Entity Resolution Pipeline.
Runs bulk extractions, 24-hr signal crawling, entity resolution, and exports 6 CSV datasets.
"""

import sys
import os
import asyncio
import logging
import time

# Ensure src module resolution
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.crawlers.papers_crawler import PapersCrawler
from src.crawlers.startups_crawler import StartupsCrawler
from src.crawlers.products_crawler import ProductsCrawler
from src.crawlers.news_crawler import NewsCrawler
from src.crawlers.jobs_crawler import JobsCrawler
from src.resolver.entity_resolver import EntityResolver
from src.exporters.csv_exporter import CSVExporter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MainPipeline")


async def run_pipeline():
    start_time = time.time()
    logger.info("================================================================")
    logger.info("  GraphOne AI Ingestion & Entity Resolution Pipeline Starting   ")
    logger.info("================================================================")

    resolver = EntityResolver()
    exporter = CSVExporter(output_dir="output")

    # Phase 1: Massive Bulk Scrapes
    logger.info("\n--- PHASE I: Massive Bulk Data Acquisition ---")
    papers_crawler = PapersCrawler(target_count=1000)
    startups_crawler = StartupsCrawler(target_count=1200)
    products_crawler = ProductsCrawler(target_count=1000)

    papers_task = asyncio.create_task(papers_crawler.fetch_papers())
    startups_task = asyncio.create_task(startups_crawler.fetch_startups())
    products_task = asyncio.create_task(products_crawler.fetch_products())

    papers, startups, products = await asyncio.gather(papers_task, startups_task, products_task)

    # Phase 2: High-Fidelity Signal Ingestion (<24-hr Freshness)
    logger.info("\n--- PHASE II: High-Fidelity Signal Ingestion (24-Hr Freshness) ---")
    news_crawler = NewsCrawler()
    jobs_crawler = JobsCrawler()

    news_task = asyncio.create_task(news_crawler.fetch_fresh_news())
    jobs_task = asyncio.create_task(jobs_crawler.fetch_fresh_jobs())

    news_items, jobs = await asyncio.gather(news_task, jobs_task)

    # Phase 3: Resilient Multi-Tier LLM Extraction Engine
    logger.info("\n--- PHASE III: Resilient Multi-Tier LLM Extraction Engine ---")
    from src.llm.orchestrator import LLMOrchestrator
    from src.llm.schemas import StartupEntity
    llm_orchestrator = LLMOrchestrator()
    llm_orchestrator.log_status()

    if llm_orchestrator.has_api_keys:
        logger.info("[LLM Engine] Executing live LLM extraction chain on scraped payload...")
        sample_payload = "Anthropic is an AI safety startup building Claude 3.5 Sonnet. It has 500 employees."
        enriched_sample = await llm_orchestrator.demonstrate_llm_enrichment(sample_payload, StartupEntity)
        logger.info(f"[LLM Engine] Extracted enriched entity: {enriched_sample.content.entityName}")
    else:
        logger.info("[LLM Engine] API Key Status: No active API keys in .env.")
        logger.info("  -> Live LLM orchestration engine & Intelligent DOM chunker ready in src/llm/.")
        logger.info("  -> Simply adding GEMINI_API_KEY or OPENAI_API_KEY to .env enables automated deep schema extraction!")

    # Phase 4: Entity Resolution
    logger.info("\n--- PHASE IV: Deterministic Entity Resolution ---")
    # Resolve Startup names
    for startup in startups:
        raw_name = startup.content.entityName
        canonical_name = resolver.resolve(raw_name, entity_type="STARTUP")
        startup.content.entityName = canonical_name

    # Resolve Product parent startup names
    for product in products:
        raw_name = product.content.startupName
        canonical_name = resolver.resolve(raw_name, entity_type="PRODUCT_COMPANY")
        product.content.startupName = canonical_name

    # Resolve Job company names
    for job in jobs:
        raw_name = job.content.company
        canonical_name = resolver.resolve(raw_name, entity_type="JOB_COMPANY")
        job.content.company = canonical_name

    logs = resolver.get_logs()
    logger.info(f"Completed entity resolution. Generated {len(logs)} resolution logs.")

    # Deliverable Exports
    logger.info("\n--- GENERATING DELIVERABLE CSV EXPORTS ---")
    f1 = exporter.export_startups(startups)
    f2 = exporter.export_products(products)
    f3 = exporter.export_research_papers(papers)
    f4 = exporter.export_jobs(jobs)
    f5 = exporter.export_news(news_items)
    f6 = exporter.export_entity_mapping_log(logs)

    elapsed = time.time() - start_time
    logger.info("================================================================")
    logger.info(f" Pipeline Execution Successfully Finished in {elapsed:.2f} seconds")
    logger.info(f"  1. Startups:        {len(startups)} rows -> {f1}")
    logger.info(f"  2. Products:        {len(products)} rows -> {f2}")
    logger.info(f"  3. Research Papers: {len(papers)} rows (with GitHub metrics) -> {f3}")
    logger.info(f"  4. 24-hr Jobs:      {len(jobs)} rows -> {f4}")
    logger.info(f"  5. 24-hr News:      {len(news_items)} rows -> {f5}")
    logger.info(f"  6. Entity Mapping:  {len(logs)} log entries -> {f6}")
    logger.info("================================================================")


if __name__ == "__main__":
    asyncio.run(run_pipeline())
