import argparse, csv, json
from pathlib import Path

FIELDS = [
    "review_id", "sentence_id", "clause_id", "clause_text",
    "previous_sentence", "sentence_text", "next_sentence",
    "destination_label", "destination_set", "sentiment_label",
    "evidence_type"
]

def main():
    p = argparse.ArgumentParser(description="Create a blank clause-level annotation CSV.")
    p.add_argument("--input", default="data/processed/clauses.jsonl")
    p.add_argument("--output", default="data/annotations/annotation_template.csv")
    a = p.parse_args()
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with Path(a.input).open(encoding="utf-8") as src, out.open("w", encoding="utf-8-sig", newline="") as dst:
        writer = csv.DictWriter(dst, fieldnames=FIELDS)
        writer.writeheader()
        for line_no, line in enumerate(src, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            writer.writerow({
                "review_id": row.get("review_id", ""), "sentence_id": row.get("sentence_id", ""),
                "clause_id": row.get("clause_id", ""), "clause_text": row.get("clause_text", ""),
                "previous_sentence": row.get("previous_sentence", ""),
                "sentence_text": row.get("sentence_text", ""), "next_sentence": row.get("next_sentence", ""),
                "destination_label": "", "destination_set": "", "sentiment_label": "",
                "evidence_type": ""
            })
            n += 1
    print(f"Annotation rows={n}; output={out}")

if __name__ == "__main__":
    main()
