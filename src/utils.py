"""Shared text/data utilities adapted from the project's existing scripts.utils.

The public function names and the core port dictionary are intentionally kept
compatible with the existing forward-window and related scripts.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd
import spacy
try:
    from ftfy import fix_text
except ImportError:  # graceful fallback; ftfy remains in requirements.txt
    def fix_text(value):
        return value

# Load models lazily so simple utilities (e.g. port matching) can be imported
# without initializing NLP models. They are still loaded only once per process.
nlp = None
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    vader = SentimentIntensityAnalyzer()
except ImportError:
    vader = None

PORTS = {"cozumel": "Cozumel", "roatan": "Roatan", "costa maya": "Costa Maya"}


def normalize_text(text: str) -> str:
    """Lowercase text for case-insensitive matching."""
    return (text or "").lower()


def clean_text(text: str) -> str:
    """Normalize common encoding, newline, dash, and smart-quote issues."""
    text = fix_text(str(text or "").replace("\n", " ").replace("\r", " "))
    text = re.sub(r"[–—−]", "-", text)
    text = re.sub(r"[“”]", '"', text)
    text = re.sub(r"[‘’]", "'", text)
    return text


def detect_ports(text: str) -> list[str]:
    """Return unique canonical port names mentioned in text.

    Ordering is deterministic (the dictionary order), unlike the original set
    return, so IDs/outputs are reproducible across runs.
    """
    text = normalize_text(text)
    found = []
    for key, canonical in PORTS.items():
        pattern = r"\b" + re.escape(key) + r"(?:'s)?\b"
        if re.search(pattern, text) and canonical not in found:
            found.append(canonical)
    return found


def _fallback_parse_jsonl_line(line: str) -> dict[str, Any] | None:
    """Best-effort fallback for malformed legacy lines; valid JSON is preferred."""
    # First try to recover a JSON object from the line without changing quotes.
    # This succeeds for lines with harmless leading/trailing text.
    start, end = line.find("{"), line.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(line[start : end + 1])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass

    # Legacy fallback: greedy review extraction is intentionally last-resort.
    id_match = re.search(r'"review_id"\s*:\s*(\d+)', line)
    name_match = re.search(r'"name"\s*:\s*"(.*?)"', line)
    review_match = re.search(r'"review"\s*:\s*"(.*)"\s*,\s*"name"', line)
    if not review_match:
        review_match = re.search(r'"review"\s*:\s*"(.*)"\s*[,}]', line)
    if not review_match:
        return None
    return {
        "review_id": int(id_match.group(1)) if id_match else None,
        "name": name_match.group(1) if name_match else "",
        "review": review_match.group(1),
    }


def load_jsonl(path: str | Path) -> pd.DataFrame:
    """Load JSONL into a DataFrame and normalize review text.

    Valid JSONL is parsed normally. Malformed lines are recovered best-effort;
    unrecoverable lines are reported and skipped, retaining legacy behavior.
    """
    data = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                obj = _fallback_parse_jsonl_line(line)
                if obj is None:
                    print(f"Skipping bad line {line_no}")
                    continue
            if not isinstance(obj, dict):
                print(f"Skipping non-object JSON record on line {line_no}")
                continue
            if isinstance(obj.get("review"), str):
                obj["review"] = clean_text(obj["review"])
            data.append(obj)
    return pd.DataFrame(data)


def split_sentences(text: str) -> list[str]:
    """Split text into sentence strings using the shared spaCy pipeline."""
    global nlp
    if nlp is None:
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError as exc:
            raise OSError(
                "spaCy model 'en_core_web_sm' is missing. Install it with: "
                "python -m spacy download en_core_web_sm"
            ) from exc
    doc = nlp(text or "")
    return [sent.text.strip() for sent in doc.sents if sent.text.strip()]


# Contrast markers are retained at the start of the following clause so the
# contrast remains visible to annotators. "Although" is deliberately excluded:
# it commonly introduces a subordinate clause rather than a separate opinion.
_CONTRAST_SPLIT_RE = re.compile(r"(?i)(?<=\s)(?=(?:but\b|however\b|yet\b))")

# Explicit subjects often signal that "and" joins two independently useful
# propositions (e.g., "the ride was short, and we had plenty of time"). The
# dependency parser is used for this rather than splitting every "and".
_INDEPENDENT_SUBJECT_DEPS = {"nsubj", "nsubjpass", "csubj", "expl"}
_COORDINATORS = {"and", "but", "yet"}


def _independent_coordination_boundaries(sentence: str) -> list[int]:
    """Return character offsets for conjunctions joining independent clauses.

    This is intentionally conservative: only split a coordinated clause when
    the conjunct has its own subject, avoiding fragments such as "short and
    smooth" or "turtles and rays". The shared spaCy model is loaded lazily by
    split_sentences; load it here as well when this helper is used directly.
    """
    global nlp
    if nlp is None:
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError as exc:
            raise OSError(
                "spaCy model 'en_core_web_sm' is missing. Install it with: "
                "python -m spacy download en_core_web_sm"
            ) from exc

    doc = nlp(sentence)
    boundaries: list[int] = []
    for token in doc:
        if token.lower_ not in _COORDINATORS or token.dep_ != "cc":
            continue
        conjunct = token.head
        if conjunct.dep_ != "conj":
            continue
        subtree = list(conjunct.subtree)
        has_own_subject = any(t.dep_ in _INDEPENDENT_SUBJECT_DEPS for t in subtree)
        if not has_own_subject:
            continue
        # For contrast markers, the dedicated split below retains the marker.
        if token.lower_ in {"but", "yet"}:
            continue
        boundaries.append(token.idx)
    return boundaries


def split_clauses(sentence: str) -> list[dict[str, Any]]:
    """Split a sentence into annotation-friendly units using conservative rules.

    1. Split at common contrast markers (but/however/yet), retaining the marker
       on the following unit.
    2. Split coordinated independent clauses joined by "and" when spaCy detects
       a separate subject. Do not split ordinary lists or adjective phrases.

    This is a heuristic, not a complete linguistic clause parser. Keep the
    original sentence and neighboring context in output for annotation.
    """
    sentence = (sentence or "").strip()
    if not sentence:
        return []

    # First split on contrast markers and then split only explicit independent
    # "and" coordinations inside each resulting part.
    contrast_parts = [
        part.strip()
        for part in _CONTRAST_SPLIT_RE.split(sentence)
        if part.strip()
    ] or [sentence]

    parts: list[str] = []
    for contrast_part in contrast_parts:
        boundaries = _independent_coordination_boundaries(contrast_part)
        if not boundaries:
            parts.append(contrast_part.strip())
            continue
        cursor = 0
        for boundary in boundaries:
            before = contrast_part[cursor:boundary].strip().rstrip(",; ")
            if before:
                parts.append(before)
            cursor = boundary + len("and")
        tail = contrast_part[cursor:].strip().lstrip(",; ")
        if tail:
            parts.append(tail)

    clauses = []
    seen_ports: set[str] = set()
    for index, part in enumerate(parts):
        ports = detect_ports(part)
        has_switch = index > 0 and bool(ports) and bool(set(ports) - seen_ports)
        clauses.append({"text": part, "ports": ports, "has_port_switch": has_switch})
        seen_ports.update(ports)
    return clauses


def get_sentiment(text: str) -> float:
    """Return the VADER compound sentiment score (range -1 to +1)."""
    if vader is None:
        raise ImportError("VADER is not installed. Run: pip install -r requirements.txt")
    return float(vader.polarity_scores(text or "")["compound"])
