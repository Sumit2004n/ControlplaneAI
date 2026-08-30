"""In-process knowledge base with deterministic retrieval.

Chunks markdown documents by section and indexes them with TF-IDF.
Works fully offline (demo mode). In real-LLM mode the same retrieval feeds
the LLM judge with candidate evidence.
"""
import math
import re
from dataclasses import dataclass
from pathlib import Path

from ..config import KNOWLEDGE_BASE_DIR

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "of", "to", "in", "on",
    "for", "and", "or", "with", "by", "at", "from", "as", "it", "its", "this", "that",
    "do", "does", "did", "can", "may", "must", "will", "shall", "should", "would",
    "per", "any", "all", "our", "your", "their", "his", "her", "he", "she", "they",
    "we", "you", "i", "not", "no", "if", "than", "then", "so", "such", "these", "those",
    "have", "has", "had", "into", "about", "up", "out", "also", "only", "more", "most",
}


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    # naive singularization so "leaves"/"leave" and "days"/"day" match
    return [t[:-1] if t.endswith("s") and len(t) > 3 and not t.isdigit() else t for t in tokens]


def content_tokens(text: str) -> set[str]:
    return {t for t in tokenize(text) if t not in STOPWORDS}


def extract_numbers(text: str) -> set[str]:
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


@dataclass
class Chunk:
    doc_id: str
    doc_name: str
    section: str
    text: str


class KnowledgeBase:
    def __init__(self, kb_dir: Path = KNOWLEDGE_BASE_DIR):
        self.kb_dir = kb_dir
        self.chunks: list[Chunk] = []
        self._tf: list[dict[str, float]] = []
        self._idf: dict[str, float] = {}
        self.load()

    def load(self) -> None:
        self.chunks = []
        if self.kb_dir.exists():
            for path in sorted(self.kb_dir.glob("*.md")):
                self._chunk_file(path)
        self._build_index()

    def _chunk_file(self, path: Path) -> None:
        text = path.read_text(encoding="utf-8")
        doc_name = path.stem.replace("_", " ").title()
        title_match = re.match(r"#\s+(.+)", text)
        if title_match:
            doc_name = title_match.group(1).strip()
        sections = re.split(r"\n##\s+", text)
        for sec in sections[1:]:
            lines = sec.strip().splitlines()
            section_title = lines[0].strip()
            body = " ".join(line.strip() for line in lines[1:] if line.strip())
            if body:
                self.chunks.append(Chunk(doc_id=path.stem, doc_name=doc_name, section=section_title, text=body))

    def _build_index(self) -> None:
        self._tf = []
        df: dict[str, int] = {}
        docs_tokens = []
        for chunk in self.chunks:
            tokens = [t for t in tokenize(chunk.text) if t not in STOPWORDS]
            docs_tokens.append(tokens)
            for t in set(tokens):
                df[t] = df.get(t, 0) + 1
        n = max(len(self.chunks), 1)
        self._idf = {t: math.log((1 + n) / (1 + c)) + 1 for t, c in df.items()}
        for tokens in docs_tokens:
            tf: dict[str, float] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            total = max(len(tokens), 1)
            self._tf.append({t: (c / total) * self._idf.get(t, 1.0) for t, c in tf.items()})

    def search(self, query: str, k: int = 3) -> list[tuple[Chunk, float, float]]:
        """Returns (chunk, cosine_score, token_overlap) sorted by relevance."""
        q_tokens = [t for t in tokenize(query) if t not in STOPWORDS]
        if not q_tokens or not self.chunks:
            return []
        q_tf: dict[str, float] = {}
        for t in q_tokens:
            q_tf[t] = q_tf.get(t, 0) + 1
        q_vec = {t: (c / len(q_tokens)) * self._idf.get(t, 1.0) for t, c in q_tf.items()}
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0

        q_content = {t for t in q_tokens if not t.isdigit()}
        results = []
        for i, chunk in enumerate(self.chunks):
            d_vec = self._tf[i]
            dot = sum(v * d_vec.get(t, 0.0) for t, v in q_vec.items())
            d_norm = math.sqrt(sum(v * v for v in d_vec.values())) or 1.0
            cosine = dot / (q_norm * d_norm)
            c_tokens = {t for t in content_tokens(chunk.text) if not t.isdigit()}
            overlap = len(q_content & c_tokens) / max(len(q_content), 1)
            results.append((chunk, cosine, overlap))
        results.sort(key=lambda r: (r[1] + r[2]), reverse=True)
        return results[:k]


_kb: KnowledgeBase | None = None


def get_kb() -> KnowledgeBase:
    global _kb
    if _kb is None:
        _kb = KnowledgeBase()
    return _kb
