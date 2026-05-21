from collections.abc import Iterable
from time import sleep

from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone, ServerlessSpec

from app.core.config import Settings
from app.services.documents import PolicyChunk


EMBEDDING_DIMENSIONS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}


def require_vector_config(settings: Settings) -> None:
    missing = []
    if not settings.openai_api_key:
        missing.append("OPENAI_API_KEY")
    if not settings.pinecone_api_key:
        missing.append("PINECONE_API_KEY")
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")


def get_embeddings(settings: Settings) -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)


def get_pinecone_index(settings: Settings):
    require_vector_config(settings)
    pc = Pinecone(api_key=settings.pinecone_api_key)
    existing = [index["name"] for index in pc.list_indexes()]
    if settings.pinecone_index_name not in existing:
        pc.create_index(
            name=settings.pinecone_index_name,
            dimension=EMBEDDING_DIMENSIONS.get(settings.embedding_model, 1536),
            metric="cosine",
            spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
        )
        while not pc.describe_index(settings.pinecone_index_name).status["ready"]:
            sleep(1)
    return pc.Index(settings.pinecone_index_name)


def batched(items: list, batch_size: int) -> Iterable[list]:
    for idx in range(0, len(items), batch_size):
        yield items[idx : idx + batch_size]


def upsert_chunks(settings: Settings, chunks: list[PolicyChunk]) -> int:
    index = get_pinecone_index(settings)
    embeddings = get_embeddings(settings)
    indexed = 0
    for batch in batched(chunks, 64):
        vectors = embeddings.embed_documents([chunk.text for chunk in batch])
        index.upsert(
            vectors=[
                {
                    "id": chunk.id,
                    "values": vector,
                    "metadata": {
                        "text": chunk.text,
                        "policy_name": chunk.policy_name,
                        "category": chunk.category,
                        "framework": chunk.framework,
                        "page": chunk.page,
                        "section": chunk.section or "",
                    },
                }
                for chunk, vector in zip(batch, vectors, strict=True)
            ]
        )
        indexed += len(batch)
    return indexed


def semantic_search(settings: Settings, query: str, top_k: int, metadata_filter: dict | None = None) -> list[dict]:
    index = get_pinecone_index(settings)
    embedding = get_embeddings(settings).embed_query(query)
    response = index.query(
        vector=embedding,
        top_k=top_k,
        include_metadata=True,
        filter=metadata_filter or None,
    )
    matches = []
    for match in response.get("matches", []):
        metadata = match.get("metadata") or {}
        metadata["id"] = match.get("id")
        metadata["vector_score"] = float(match.get("score", 0.0))
        matches.append(metadata)
    return matches
