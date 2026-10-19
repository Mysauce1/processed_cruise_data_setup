import argparse
import json
from pathlib import Path

from utils import load_jsonl, split_sentences, split_clauses


def main():
    parser = argparse.ArgumentParser(description="Create stable clause-level rows from sampled reviews.")
    parser.add_argument("--input", default="data/processed/selected_reviews.jsonl")
    parser.add_argument("--output", default="data/processed/clauses.jsonl")
    args = parser.parse_args()

    frame = load_jsonl(args.input)
    if "review" not in frame.columns:
        raise SystemExit("Input contains no usable 'review' field.")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    seen_ids = set()
    written = 0
    review_count = 0

    with out.open("w", encoding="utf-8") as handle:
        for i, row in enumerate(frame.to_dict(orient="records"), 1):
            review = row.get("review")
            if not isinstance(review, str) or not review.strip():
                continue
            rid = str(row.get("review_id") or f"review_{i:06d}")
            if rid in seen_ids:
                raise ValueError(f"Duplicate review_id: {rid}")
            seen_ids.add(rid)
            review_count += 1
            sentences = split_sentences(review)

            for sentence_index, sentence in enumerate(sentences, 1):
                sid = f"{rid}-S{sentence_index:03d}"
                previous_sentence = sentences[sentence_index - 2] if sentence_index > 1 else ""
                next_sentence = sentences[sentence_index] if sentence_index < len(sentences) else ""
                clauses = split_clauses(sentence)
                for clause_index, clause in enumerate(clauses, 1):
                    text = clause["text"]
                    record = {
                        "review_id": rid,
                        "sentence_id": sid,
                        "clause_id": f"{sid}-C{clause_index:02d}",
                        "review_text": review,
                        "sentence_text": sentence,
                        "clause_text": text,
                        "clause_ports_detected": clause["ports"],
                        "has_port_switch": clause["has_port_switch"],
                        "previous_sentence": previous_sentence,
                        "next_sentence": next_sentence,
                        "word_count": row.get("word_count"),
                        "length_band": row.get("length_band"),
                    }
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                    written += 1

    print(f"Reviews processed={review_count}; clause rows={written}; output={out}")


if __name__ == "__main__":
    main()
