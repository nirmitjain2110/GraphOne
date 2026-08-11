"""
Intelligent HTML Cleaner & Chunking Engine.
Prevents HTTP 413 (Payload Too Large) by semantically cleaning & chunking content within LLM token bounds.
"""

import re
from typing import List
from bs4 import BeautifulSoup


class IntelligentChunker:
    """Cleans raw HTML/Text and chunks large documents safely."""

    def __init__(self, max_chunk_chars: int = 12000, overlap_chars: int = 500):
        self.max_chunk_chars = max_chunk_chars
        self.overlap_chars = overlap_chars

    def clean_html(self, raw_html: str) -> str:
        """Strips scripts, styles, metadata, and DOM noise, returning clean markdown-like text."""
        if not raw_html:
            return ""

        try:
            soup = BeautifulSoup(raw_html, "lxml")
        except Exception:
            soup = BeautifulSoup(raw_html, "html.parser")

        # Remove irrelevant tags
        for element in soup(["script", "style", "nav", "footer", "header", "iframe", "svg", "noscript", "form"]):
            element.decompose()

        # Extract text content cleanly
        lines = []
        for element in soup.stripped_strings:
            text = element.strip()
            if text and len(text) > 2:
                lines.append(text)

        cleaned_text = "\n".join(lines)
        # Normalize repetitive newlines/spaces
        cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
        cleaned_text = re.sub(r"[ \t]+", " ", cleaned_text)
        return cleaned_text.strip()

    def chunk_text(self, text: str) -> List[str]:
        """Slices clean text into chunk payloads guaranteed to fit under max_chunk_chars."""
        if not text:
            return []

        if len(text) <= self.max_chunk_chars:
            return [text]

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + self.max_chunk_chars, text_len)

            # Try to break at a clean paragraph or sentence boundary
            if end < text_len:
                paragraph_break = text.rfind("\n\n", start, end)
                if paragraph_break != -1 and paragraph_break > start + (self.max_chunk_chars // 2):
                    end = paragraph_break + 2
                else:
                    sentence_break = text.rfind(". ", start, end)
                    if sentence_break != -1 and sentence_break > start + (self.max_chunk_chars // 2):
                        end = sentence_break + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - self.overlap_chars if end < text_len else text_len

        return chunks
