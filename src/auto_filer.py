from __future__ import annotations

import argparse
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}
STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "page",
    "of",
    "to",
    "in",
    "on",
    "at",
    "by",
    "our",
    "your",
    "church",
}

DOC_TYPE_KEYWORDS = {
    "attendance_sheet": ["attendance sheet", "total attendance", "members", "visitors"],
    "church_bulletin": [
        "voice of the cross",
        "lutheran church",
        "the service",
        "ushers",
        "this lord's day",
        "welcome to our visitors",
    ],
    "minutes": ["minutes", "meeting", "agenda", "motion", "quorum"],
    "record": ["record", "register", "log", "archive", "ledger"],
    "notes": ["notes", "memo", "memorandum", "draft"],
    "letter": ["dear", "sincerely", "regards", "letterhead"],
    "report": ["report", "summary", "analysis", "findings"],
}


@dataclass
class RenameResult:
    source: Path
    target: Path
    reason: str


def iter_images(input_dir: Path, recursive: bool) -> Iterable[Path]:
    globber = input_dir.rglob if recursive else input_dir.glob
    for path in globber("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
            yield path


def extract_ocr_text(image_path: Path, conf_threshold: int) -> str:
    import pytesseract
    from PIL import Image

    data = pytesseract.image_to_data(Image.open(image_path), output_type=pytesseract.Output.DICT)
    chunks: list[str] = []
    for text, conf in zip(data["text"], data["conf"], strict=False):
        if not text or not text.strip():
            continue
        try:
            numeric_conf = int(float(conf))
        except ValueError:
            continue
        if numeric_conf >= conf_threshold:
            chunks.append(text.strip())
    return " ".join(chunks)


def detect_doc_type(text: str) -> str:
    lower = text.lower()
    scores: dict[str, int] = {}
    for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            score += lower.count(keyword)
        scores[doc_type] = score

    doc_type, score = max(scores.items(), key=lambda item: item[1])
    return doc_type if score > 0 else "unknown"


def _normalize_year(year_text: str) -> int:
    year = int(year_text)
    if year < 100:
        return 2000 + year if year < 70 else 1900 + year
    return year


def extract_date(text: str) -> str:
    patterns = [
        r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b",
        r"\b(\d{1,2})/(\d{1,2})/(\d{2,4})\b",
        r"\b(\d{1,2})-(\d{1,2})-(\d{2,4})\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue

        groups = match.groups()
        try:
            if pattern.startswith("\\b(\\d{4})"):
                year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
            else:
                month, day, year_raw = int(groups[0]), int(groups[1]), groups[2]
                year = _normalize_year(year_raw)
            parsed = datetime(year=year, month=month, day=day)
        except ValueError:
            continue

        if 1900 <= parsed.year <= datetime.now().year + 1:
            return parsed.strftime("%Y-%m-%d")

    month_name = re.search(
        r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\s+(\d{1,2}),?\s+(\d{2,4})\b",
        text,
        re.IGNORECASE,
    )
    if month_name:
        month_map = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "sept": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }
        month = month_map[month_name.group(1).lower()]
        day = int(month_name.group(2))
        year = _normalize_year(month_name.group(3))
        try:
            parsed = datetime(year=year, month=month, day=day)
            if 1900 <= parsed.year <= datetime.now().year + 1:
                return parsed.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return "undated"


def slugify_title(text: str, max_words: int = 6) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    filtered = [w for w in words if w not in STOPWORDS and len(w) > 1]
    if not filtered:
        return "untitled"

    most_common = [word for word, _ in Counter(filtered).most_common(max_words)]
    return "_".join(most_common)


def infer_title(text: str, doc_type: str) -> str:
    lower = text.lower()
    if doc_type == "attendance_sheet":
        return "attendance_sheet"
    if doc_type == "church_bulletin":
        if "voice of the cross" in lower:
            return "voice_of_the_cross"
        return "church_bulletin"
    return slugify_title(text)


def create_filename(doc_type: str, date: str, title: str, ext: str, counter: int) -> str:
    return f"{doc_type}_{date}_{title}_{counter}{ext.lower()}"


def make_relative_folder(doc_type: str, date: str) -> Path:
    year = date[:4] if date != "undated" else "undated"
    return Path(doc_type) / year


def propose_rename(
    path: Path,
    output_root: Path,
    conf_threshold: int,
    min_text_chars: int,
    collision_counter: dict[str, int],
) -> RenameResult:
    text = extract_ocr_text(path, conf_threshold=conf_threshold)
    if len(text) < min_text_chars:
        doc_type = "unknown"
        date = "undated"
        title = "untitled"
        reason = "low_ocr_text"
    else:
        doc_type = detect_doc_type(text)
        date = extract_date(text)
        title = infer_title(text, doc_type)
        reason = "ocr_inference"

    key = f"{doc_type}_{date}_{title}{path.suffix.lower()}"
    collision_counter[key] += 1
    filename = create_filename(doc_type, date, title, path.suffix, collision_counter[key])

    folder = output_root / make_relative_folder(doc_type, date)
    return RenameResult(path, folder / filename, reason)


def run(args: argparse.Namespace) -> int:
    input_dir = Path(args.input).resolve()
    if not input_dir.exists() or not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    output_root = Path(args.output).resolve() if args.output else input_dir

    images = sorted(iter_images(input_dir, recursive=args.recursive))
    if not images:
        print("No images found.")
        return 0

    collision_counter: dict[str, int] = Counter()
    proposals: list[RenameResult] = []

    for image_path in images:
        proposal = propose_rename(
            image_path,
            output_root=output_root,
            conf_threshold=args.conf_threshold,
            min_text_chars=args.min_text_chars,
            collision_counter=collision_counter,
        )
        proposals.append(proposal)

    for item in proposals:
        print(f"[{item.reason}] {item.source} -> {item.target}")

    if args.dry_run:
        print("Dry run complete. No files moved/renamed.")
        return 0

    for item in proposals:
        if item.source == item.target:
            continue
        item.target.parent.mkdir(parents=True, exist_ok=True)
        item.source.rename(item.target)

    print(f"Filed {len(proposals)} file(s).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Auto-file scanned image files using OCR")
    parser.add_argument("--input", required=True, help="Directory containing scanned images")
    parser.add_argument("--output", help="Output root directory for organized files (defaults to input)")
    parser.add_argument("--recursive", action="store_true", help="Scan subdirectories recursively")
    parser.add_argument("--dry-run", action="store_true", help="Preview proposed moves without changing files")
    parser.add_argument("--min-text-chars", type=int, default=20, help="Minimum OCR text length for inference")
    parser.add_argument("--conf-threshold", type=int, default=40, help="Minimum OCR confidence per token")
    return parser


if __name__ == "__main__":
    cli_args = build_parser().parse_args()
    raise SystemExit(run(cli_args))
