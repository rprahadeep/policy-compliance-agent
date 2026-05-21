import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any


def load_analytics(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"events": []}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_analytics(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def record_query(path: Path, question: str, status: str, risk_level: str, risk_score: int) -> None:
    data = load_analytics(path)
    data.setdefault("events", []).append(
        {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "question": question,
            "status": status,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "topics": extract_topics(question),
        }
    )
    save_analytics(path, data)


def summarize_analytics(path: Path) -> dict[str, Any]:
    events = load_analytics(path).get("events", [])
    status_counts = Counter(event.get("status", "unknown") for event in events)
    risk_counts = Counter(event.get("risk_level", "unknown") for event in events)
    topic_counts = Counter(topic for event in events for topic in event.get("topics", []))
    return {
        "total_queries": len(events),
        "compliance_status_counts": dict(status_counts),
        "risk_level_counts": dict(risk_counts),
        "top_topics": [{"topic": topic, "count": count} for topic, count in topic_counts.most_common(8)],
        "recent_queries": list(reversed(events[-8:])),
    }


def extract_topics(question: str) -> list[str]:
    stopwords = {"should", "could", "would", "about", "there", "their", "while", "with", "from", "need"}
    words = [word for word in re.findall(r"[a-zA-Z]{4,}", question.lower()) if word not in stopwords]
    return [word for word, _ in Counter(words).most_common(4)]
