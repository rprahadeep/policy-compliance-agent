import json
from pathlib import Path

from app.services.documents import PolicyChunk


def save_chunks(path: Path, chunks: list[PolicyChunk]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk.to_record(), ensure_ascii=False) + "\n")


def load_chunks(path: Path) -> list[dict]:
    if not path.exists():
        return []
    chunks = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                chunks.append(json.loads(line))
    return chunks
