"""
BM25-based tool registry with jieba Chinese tokenisation.
Lazily imports all tool modules on first query so server startup stays fast.
"""
from __future__ import annotations

_bm25 = None
_corpus_tools: list[dict] | None = None


def _tokenize(text: str) -> list[str]:
    try:
        import jieba
        jieba.setLogLevel(60)  # suppress all jieba output
        return list(jieba.cut(text))
    except ImportError:
        # Fallback: split on non-alphanumeric
        import re
        return re.findall(r"[A-Za-z0-9一-鿿]+", text)


def _build() -> None:
    global _bm25, _corpus_tools
    from . import tools  # triggers @tool registration for all modules
    from .tools._base import all_tools
    from rank_bm25 import BM25Okapi

    tool_list = all_tools()
    if not tool_list:
        return
    corpus = []
    for t in tool_list:
        text = f"{t['name_zh']} {t['desc_zh']} {t['desc_en']} {t['name']}"
        corpus.append(_tokenize(text))
    _bm25 = BM25Okapi(corpus)
    _corpus_tools = tool_list


def retrieve_tools(query: str, k: int = 5) -> list[dict]:
    """Return top-k tool descriptors (without the 'fn' key) for the given query."""
    global _bm25, _corpus_tools
    if _bm25 is None:
        _build()
    if _bm25 is None or not _corpus_tools:
        return []
    tokens = _tokenize(query)
    scores = _bm25.get_scores(tokens)
    top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    return [{k: v for k, v in _corpus_tools[i].items() if k != "fn"} for i in top_idx]


def get_tool(name: str) -> dict | None:
    """Return tool descriptor (with 'fn') by function name."""
    if _corpus_tools is None:
        _build()
    from .tools._base import get_tool as _gt
    return _gt(name)


def all_tool_descriptors() -> list[dict]:
    """Return all registered tools without 'fn' key (for API listing)."""
    if _corpus_tools is None:
        _build()
    from .tools._base import all_tools
    return [{k: v for k, v in t.items() if k != "fn"} for t in all_tools()]


def invalidate() -> None:
    """Force rebuild on next query (used by build_index.py)."""
    global _bm25, _corpus_tools
    _bm25 = None
    _corpus_tools = None
