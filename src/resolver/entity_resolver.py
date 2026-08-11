"""
Deterministic Entity Resolution Engine.
Canonicalizes entity names against a seed list of known AI organizations,
handling string noise, legal suffixes, and spacing variations.
"""

import re
import logging
from typing import Tuple, List, Dict
from rapidfuzz import fuzz, process

from src.llm.schemas import EntityMappingLog

logger = logging.getLogger("EntityResolver")


# Seed list of 50 Canonical AI Startups & Organizations
SEED_CANONICAL_ENTITIES = [
    "OpenAI",
    "Anthropic",
    "Google DeepMind",
    "Hugging Face",
    "Midjourney",
    "Stability AI",
    "Mistral AI",
    "Cohere",
    "Perplexity AI",
    "Scale AI",
    "ElevenLabs",
    "Runway",
    "Jasper",
    "Character.AI",
    "Harvey",
    "Pinecone",
    "Weaviate",
    "Qdrant",
    "Modal",
    "Anyscale",
    "Together AI",
    "Replicate",
    "LangChain",
    "LlamaIndex",
    "Cursor",
    "Synthesia",
    "Typeface",
    "Codeium",
    "Writer",
    "Glean",
    "Moveworks",
    "Unify",
    "Baseten",
    "Vellum",
    "AssemblyAI",
    "DeepL",
    "Covariant",
    "Imbue",
    "Adept AI",
    "Inflection AI",
    "SambaNova Systems",
    "Cerebras Systems",
    "Groq",
    "Weights & Biases",
    "OctoAI",
    "Fireworks AI",
    "Cleanlab",
    "Arthur AI",
    "Arize AI",
    "Shield AI"
]

# Explicit alias dictionary for edge cases
ALIAS_MAP: Dict[str, str] = {
    "open ai": "OpenAI",
    "openai inc": "OpenAI",
    "openai inc.": "OpenAI",
    "openai lp": "OpenAI",
    "anthropic pbc": "Anthropic",
    "anthropic ai": "Anthropic",
    "deepmind": "Google DeepMind",
    "huggingface": "Hugging Face",
    "huggingface inc": "Hugging Face",
    "stability": "Stability AI",
    "stability.ai": "Stability AI",
    "mistral": "Mistral AI",
    "cohere ai": "Cohere",
    "perplexity": "Perplexity AI",
    "eleven labs": "ElevenLabs",
    "runwayml": "Runway",
    "runway ml": "Runway",
    "character ai": "Character.AI",
    "pinecone io": "Pinecone",
    "together.ai": "Together AI",
    "langchain inc": "LangChain",
    "llamaindex": "LlamaIndex",
    "cursor ai": "Cursor",
    "anyspheres": "Cursor",
    "groq inc": "Groq",
    "wandb": "Weights & Biases",
    "weights and biases": "Weights & Biases",
}


class EntityResolver:
    """Canonicalizes messy organization and product strings dynamically."""

    def __init__(self, canonical_list: List[str] = None):
        self.canonical_entities = canonical_list or SEED_CANONICAL_ENTITIES
        # Pre-normalize canonical list for fast lookup
        self.normalized_canonical_map = {
            self._normalize_string(name): name for name in self.canonical_entities
        }
        self.mapping_logs: List[EntityMappingLog] = []

    def _normalize_string(self, text: str) -> str:
        """Removes legal suffixes, punctuation, extra whitespace, and lowercases text."""
        if not text:
            return ""

        s = text.lower().strip()
        # Strip common company suffixes
        legal_suffixes = [
            r"\binc\.?\b", r"\bllc\.?\b", r"\bcorp\.?\b", r"\bcorporation\b",
            r"\bltd\.?\b", r"\bpte\.?\b", r"\bpbc\.?\b", r"\bco\.?\b", r"\btechnologies\b",
            r"\blabs\b", r"\bgroup\b", r"\bio\b"
        ]
        for suffix in legal_suffixes:
            s = re.sub(suffix, "", s)

        # Remove special characters
        s = re.sub(r"[^\w\s]", " ", s)
        # Collapse multiple spaces
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def resolve(self, raw_name: str, entity_type: str = "STARTUP") -> str:
        """Resolves a raw entity string to a canonical string, logging the mapping."""
        if not raw_name or not raw_name.strip():
            return raw_name

        raw_clean = raw_name.strip()
        norm_raw = self._normalize_string(raw_clean)

        # 1. Check exact alias map
        if norm_raw in ALIAS_MAP:
            canonical = ALIAS_MAP[norm_raw]
            self._log_mapping(raw_clean, canonical, 100.0, "AliasDict", entity_type)
            return canonical

        # 2. Check direct normalized canonical match
        if norm_raw in self.normalized_canonical_map:
            canonical = self.normalized_canonical_map[norm_raw]
            self._log_mapping(raw_clean, canonical, 100.0, "DirectMatch", entity_type)
            return canonical

        # 3. Perform fuzzy matching against canonical database
        best_match = process.extractOne(
            norm_raw,
            self.normalized_canonical_map.keys(),
            scorer=fuzz.token_sort_ratio
        )

        if best_match:
            matched_norm, score, _ = best_match
            if score >= 82.0:
                canonical = self.normalized_canonical_map[matched_norm]
                self._log_mapping(raw_clean, canonical, score, "FuzzyMatch", entity_type)
                return canonical

        # 4. If no canonical match above threshold, title-case the cleaned name
        canonical = raw_clean.title()
        self._log_mapping(raw_clean, canonical, 50.0, "PassthroughTitleCase", entity_type)
        return canonical

    def _log_mapping(self, raw: str, canonical: str, score: float, method: str, entity_type: str):
        log_entry = EntityMappingLog(
            raw_name=raw,
            canonical_name=canonical,
            match_score=score,
            method=method,
            entity_type=entity_type
        )
        self.mapping_logs.append(log_entry)

    def get_logs(self) -> List[EntityMappingLog]:
        return self.mapping_logs
