import math
import re
from collections import Counter
from typing import Any

from app.core.config import Settings
from app.models.schemas import Citation, QueryFilters
from app.services.local_store import load_chunks
from app.services.pinecone_store import semantic_search


AUTHORITY_WEIGHTS = {
    "Security Assessment and Authorization": 1.12,
    "Identification and Authentication": 1.1,
    "Information Security": 1.05,
    "System and Services Acquisition": 1.0,
}


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", text.lower())


def keyword_scores(query: str, chunks: list[dict]) -> dict[str, float]:
    query_terms = Counter(tokenize(query))
    if not query_terms:
        return {}
    scores: dict[str, float] = {}
    total_docs = max(len(chunks), 1)
    document_frequency = Counter()
    tokenized_chunks = {}
    for chunk in chunks:
        tokens = tokenize(chunk.get("text", ""))
        tokenized_chunks[chunk["id"]] = Counter(tokens)
        for term in set(tokens):
            document_frequency[term] += 1
    for chunk_id, term_counts in tokenized_chunks.items():
        score = 0.0
        for term, q_count in query_terms.items():
            if term not in term_counts:
                continue
            idf = math.log((total_docs + 1) / (document_frequency[term] + 1)) + 1
            score += q_count * term_counts[term] * idf
        scores[chunk_id] = score
    max_score = max(scores.values(), default=0.0)
    return {chunk_id: score / max_score for chunk_id, score in scores.items() if max_score > 0}


def matches_filters(chunk: dict, filters: QueryFilters) -> bool:
    return all(
        [
            not filters.category or chunk.get("category") == filters.category,
            not filters.framework or chunk.get("framework") == filters.framework,
            not filters.policy_name or chunk.get("policy_name") == filters.policy_name,
        ]
    )


def hybrid_retrieve(settings: Settings, query: str, filters: QueryFilters, top_k: int) -> list[dict[str, Any]]:
    local_chunks = [chunk for chunk in load_chunks(settings.local_store) if matches_filters(chunk, filters)]
    keyword = keyword_scores(query, local_chunks)
    local_by_id = {chunk["id"]: chunk for chunk in local_chunks}
    metadata_filter = filters.to_metadata_filter()
    semantic = semantic_search(settings, query, top_k=max(top_k * 3, 12), metadata_filter=metadata_filter)

    combined: dict[str, dict[str, Any]] = {}
    for item in semantic:
        chunk_id = item["id"]
        combined[chunk_id] = {**local_by_id.get(chunk_id, {}), **item}
    for chunk_id, score in sorted(keyword.items(), key=lambda row: row[1], reverse=True)[: top_k * 3]:
        if chunk_id not in combined and chunk_id in local_by_id:
            combined[chunk_id] = {**local_by_id[chunk_id], "vector_score": 0.0}
        if chunk_id in combined:
            combined[chunk_id]["keyword_score"] = score

    reranked = []
    for item in combined.values():
        vector_score = float(item.get("vector_score", 0.0))
        keyword_score = float(item.get("keyword_score", keyword.get(item.get("id", ""), 0.0)))
        authority = AUTHORITY_WEIGHTS.get(item.get("category"), 1.0)
        item["score"] = ((0.72 * vector_score) + (0.28 * keyword_score)) * authority
        reranked.append(item)
    return sorted(reranked, key=lambda row: row.get("score", 0.0), reverse=True)[:top_k]


def to_citations(chunks: list[dict]) -> list[Citation]:
    citations = []
    for chunk in chunks:
        text = chunk.get("text", "")
        citations.append(
            Citation(
                source_id=chunk.get("id", ""),
                policy_name=chunk.get("policy_name", "Unknown policy"),
                page=int(chunk.get("page") or 0),
                section=chunk.get("section") or None,
                category=chunk.get("category"),
                framework=chunk.get("framework"),
                excerpt=text[:500],
                score=round(float(chunk.get("score", 0.0)), 4),
            )
        )
    return citations
