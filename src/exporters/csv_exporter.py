"""
CSV Exporter Module for Google Sheets compatibility.
Generates 6 formatted CSV files corresponding to the 6 Google Sheets tabs.
Handles file lock PermissionErrors gracefully using timestamp fallbacks.
"""

import os
import csv
import time
import logging
from typing import List

from src.llm.schemas import (
    StartupEntity,
    ProductEntity,
    ResearchPaperEntity,
    JobEntity,
    NewsEntity,
    EntityMappingLog
)

logger = logging.getLogger("CSVExporter")


class CSVExporter:
    """Exports pipeline entities into 6 clean CSV files matching Google Sheets deliverable tabs."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _safe_write_csv(self, filename: str, fieldnames: List[str], rows: List[dict]) -> str:
        filepath = os.path.join(self.output_dir, filename)
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            return filepath
        except PermissionError:
            base, ext = os.path.splitext(filename)
            fallback_filename = f"{base}_export_{int(time.time())}{ext}"
            filepath = os.path.join(self.output_dir, fallback_filename)
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            logger.warning(f"File '{filename}' locked by another process. Saved to fallback: {filepath}")
            return filepath

    def export_startups(self, startups: List[StartupEntity], filename: str = "startups.csv") -> str:
        fieldnames = ["schemaVersion", "recordType", "source_name", "source_url", "entityName", "employeeCount", "description", "category", "collectedAt"]
        rows = [
            {
                "schemaVersion": s.schemaVersion,
                "recordType": s.recordType,
                "source_name": s.source.name,
                "source_url": s.source.url,
                "entityName": s.content.entityName,
                "employeeCount": s.content.data.employeeCount if s.content.data else "",
                "description": s.content.data.description if s.content.data else "",
                "category": s.content.data.category if s.content.data else "",
                "collectedAt": s.collectedAt
            }
            for s in startups
        ]
        filepath = self._safe_write_csv(filename, fieldnames, rows)
        logger.info(f"Exported {len(startups)} startup records to {filepath}")
        return filepath

    def export_products(self, products: List[ProductEntity], filename: str = "products.csv") -> str:
        fieldnames = ["schemaVersion", "recordType", "source_name", "source_url", "startupName", "productName", "pricingModel", "description", "collectedAt"]
        rows = [
            {
                "schemaVersion": p.schemaVersion,
                "recordType": p.recordType,
                "source_name": p.source.name,
                "source_url": p.source.url,
                "startupName": p.content.startupName,
                "productName": p.content.productName,
                "pricingModel": p.content.pricingModel.value if hasattr(p.content.pricingModel, 'value') else p.content.pricingModel,
                "description": p.content.description or "",
                "collectedAt": p.collectedAt
            }
            for p in products
        ]
        filepath = self._safe_write_csv(filename, fieldnames, rows)
        logger.info(f"Exported {len(products)} product records to {filepath}")
        return filepath

    def export_research_papers(self, papers: List[ResearchPaperEntity], filename: str = "research_papers.csv") -> str:
        fieldnames = ["schemaVersion", "recordType", "source_name", "source_url", "title", "authors", "paper_url", "github_url", "github_stars", "published_date", "collectedAt"]
        rows = [
            {
                "schemaVersion": paper.schemaVersion,
                "recordType": paper.recordType,
                "source_name": paper.source.name,
                "source_url": paper.source.url,
                "title": paper.content.title,
                "authors": "; ".join(paper.content.authors),
                "paper_url": paper.content.paper_url,
                "github_url": paper.content.github_url or "",
                "github_stars": paper.content.github_stars or 0,
                "published_date": paper.content.published_date,
                "collectedAt": paper.collectedAt
            }
            for paper in papers
        ]
        filepath = self._safe_write_csv(filename, fieldnames, rows)
        logger.info(f"Exported {len(papers)} research paper records to {filepath}")
        return filepath

    def export_jobs(self, jobs: List[JobEntity], filename: str = "jobs.csv") -> str:
        fieldnames = ["schemaVersion", "recordType", "source_name", "source_url", "company", "title", "date", "is_remote", "role_family", "collectedAt"]
        rows = [
            {
                "schemaVersion": j.schemaVersion,
                "recordType": j.recordType,
                "source_name": j.source.name,
                "source_url": j.source.url,
                "company": j.content.company,
                "title": j.content.title,
                "date": j.content.date,
                "is_remote": j.content.is_remote,
                "role_family": j.content.role_family,
                "collectedAt": j.collectedAt
            }
            for j in jobs
        ]
        filepath = self._safe_write_csv(filename, fieldnames, rows)
        logger.info(f"Exported {len(jobs)} job records to {filepath}")
        return filepath

    def export_news(self, news_items: List[NewsEntity], filename: str = "news.csv") -> str:
        fieldnames = ["schemaVersion", "recordType", "source_name", "source_url", "title", "published_date", "summary", "full_text", "collectedAt"]
        rows = [
            {
                "schemaVersion": n.schemaVersion,
                "recordType": n.recordType,
                "source_name": n.source.name,
                "source_url": n.source.url,
                "title": n.content.title,
                "published_date": n.content.published_date,
                "summary": n.content.summary or "",
                "full_text": n.content.full_text or "",
                "collectedAt": n.collectedAt
            }
            for n in news_items
        ]
        filepath = self._safe_write_csv(filename, fieldnames, rows)
        logger.info(f"Exported {len(news_items)} news records to {filepath}")
        return filepath

    def export_entity_mapping_log(self, logs: List[EntityMappingLog], filename: str = "entity_mapping_log.csv") -> str:
        fieldnames = ["raw_name", "canonical_name", "match_score", "method", "entity_type", "timestamp"]
        rows = [
            {
                "raw_name": log.raw_name,
                "canonical_name": log.canonical_name,
                "match_score": log.match_score,
                "method": log.method,
                "entity_type": log.entity_type,
                "timestamp": log.timestamp
            }
            for log in logs
        ]
        filepath = self._safe_write_csv(filename, fieldnames, rows)
        logger.info(f"Exported {len(logs)} entity resolution log entries to {filepath}")
        return filepath
