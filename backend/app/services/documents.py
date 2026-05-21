from dataclasses import asdict, dataclass
from pathlib import Path
import re

from pypdf import PdfReader


@dataclass
class PolicyPage:
    policy_name: str
    category: str
    framework: str
    page: int
    text: str


@dataclass
class PolicyChunk:
    id: str
    text: str
    policy_name: str
    category: str
    framework: str
    page: int
    section: str | None

    def to_record(self) -> dict:
        return asdict(self)


CATEGORY_MAP = {
    "Identification-and-Authentication-Policy": "Identification and Authentication",
    "Information-Security-Policy": "Information Security",
    "Security-Assessment-and-Authorization-Policy": "Security Assessment and Authorization",
    "System-and-Services-Acquisition-Policy": "System and Services Acquisition",
}


def infer_category(path: Path) -> str:
    stem = path.stem
    return CATEGORY_MAP.get(stem, stem.replace("-", " "))


def list_policy_pdfs(policy_dir: Path) -> list[Path]:
    return sorted(policy_dir.glob("*.pdf"))


def load_policy_pages(policy_dir: Path) -> list[PolicyPage]:
    pages: list[PolicyPage] = []
    for pdf_path in list_policy_pdfs(policy_dir):
        reader = PdfReader(str(pdf_path))
        for idx, page in enumerate(reader.pages, start=1):
            text = normalize_text(page.extract_text() or "")
            if text:
                pages.append(
                    PolicyPage(
                        policy_name=pdf_path.stem.replace("-", " "),
                        category=infer_category(pdf_path),
                        framework="NIST",
                        page=idx,
                        text=text,
                    )
                )
    return pages


def count_pdf_pages(path: Path) -> int | None:
    try:
        return len(PdfReader(str(path)).pages)
    except Exception:
        return None


def normalize_text(text: str) -> str:
    text = text.replace("\uf0b7", "-")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_section(text: str) -> str | None:
    for line in text.splitlines()[:12]:
        clean = line.strip(" _:-")
        if clean.isupper() and 3 <= len(clean) <= 80:
            return clean.title()
    return None


def chunk_policy_pages(pages: list[PolicyPage], chunk_size: int = 3600, overlap: int = 450) -> list[PolicyChunk]:
    chunks: list[PolicyChunk] = []
    for policy_page in pages:
        text = policy_page.text
        start = 0
        part = 1
        while start < len(text):
            end = min(len(text), start + chunk_size)
            if end < len(text):
                boundary = max(text.rfind("\n", start, end), text.rfind(". ", start, end))
                if boundary > start + chunk_size // 2:
                    end = boundary + 1
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunk_id = f"{slug(policy_page.policy_name)}-p{policy_page.page}-c{part}"
                chunks.append(
                    PolicyChunk(
                        id=chunk_id,
                        text=chunk_text,
                        policy_name=policy_page.policy_name,
                        category=policy_page.category,
                        framework=policy_page.framework,
                        page=policy_page.page,
                        section=detect_section(chunk_text),
                    )
                )
            if end >= len(text):
                break
            start = max(0, end - overlap)
            part += 1
    return chunks


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
