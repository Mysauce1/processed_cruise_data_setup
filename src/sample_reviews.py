import argparse
import json
import random
import re
from collections import Counter
from pathlib import Path

from utils import load_jsonl

WORD_RE = re.compile(r"\b[\w]+(?:['’\-][\w]+)*\b", re.UNICODE)
BANDS = {"medium_101_199": (101, 199), "short_51_99": (51, 99), "long_200_300": (200, 300)}
SHARES = {"medium_101_199": .60, "short_51_99": .35, "long_200_300": .05}


def count_words(text):
    return len(WORD_RE.findall(text or ""))


def quotas_for(n):
    raw = {k: n * v for k, v in SHARES.items()}
    quotas = {k: int(v) for k, v in raw.items()}
    remainder_order = sorted(raw, key=lambda k: raw[k] - quotas[k], reverse=True)
    for key in remainder_order[: n - sum(quotas.values())]:
        quotas[key] += 1
    return quotas


def main():
    parser = argparse.ArgumentParser(description="Stratified random sample of cruise reviews by word count.")
    parser.add_argument("--input", default="data/raw/cruise_reviews.jsonl")
    parser.add_argument("--output", default="data/processed/selected_reviews.jsonl")
    parser.add_argument("--n", type=int, default=130)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--strict-quotas", action="store_true",
        help="Stop if any length band cannot meet its target quota instead of reallocating shortages.",
    )
    args = parser.parse_args()
    if args.n < 1:
        parser.error("--n must be positive")

    # Reuse the project's established loader and text normalization.
    frame = load_jsonl(args.input)
    if "review" not in frame.columns:
        raise SystemExit("Input contains no usable 'review' field.")
    source = frame.to_dict(orient="records")
    buckets = {key: [] for key in BANDS}
    seen_ids = set()
    outside = 0

    for i, row in enumerate(source, 1):
        review = row.get("review")
        if not isinstance(review, str) or not review.strip():
            continue
        rid = str(row.get("review_id") or f"review_{i:06d}")
        if rid in seen_ids:
            raise ValueError(f"Duplicate review_id: {rid}")
        seen_ids.add(rid)
        wc = count_words(review)
        band = next((key for key, (lo, hi) in BANDS.items() if lo <= wc <= hi), None)
        if band is None:
            outside += 1
            continue
        row.update(review_id=rid, word_count=wc, length_band=band)
        buckets[band].append(row)

    quotas = quotas_for(args.n)
    shortage = {k: (quotas[k], len(buckets[k])) for k in quotas if len(buckets[k]) < quotas[k]}
    if shortage:
        details = "; ".join(f"{k}: need {need}, have {have}" for k, (need, have) in shortage.items())
        if args.strict_quotas:
            raise SystemExit(
                f"Not enough eligible reviews for n={args.n} ({details}). "
                "Try a smaller --n or omit --strict-quotas to redistribute shortages."
            )
        # Cap each band at its available count, then distribute the remaining
        # sample slots among bands with spare records in proportion to their
        # original target shares. This keeps rare length bands without forcing
        # the whole sample to shrink when the corpus has too few long reviews.
        quotas = {key: min(quotas[key], len(buckets[key])) for key in BANDS}
        remaining = args.n - sum(quotas.values())
        while remaining > 0:
            eligible = [key for key in BANDS if quotas[key] < len(buckets[key])]
            if not eligible:
                raise SystemExit(
                    f"Only {sum(len(v) for v in buckets.values())} eligible reviews are available; "
                    f"cannot sample n={args.n}."
                )
            weights = {key: SHARES[key] for key in eligible}
            weight_total = sum(weights.values())
            raw_add = {key: remaining * weights[key] / weight_total for key in eligible}
            add = {key: min(len(buckets[key]) - quotas[key], int(raw_add[key])) for key in eligible}
            for key in eligible:
                quotas[key] += add[key]
            remaining = args.n - sum(quotas.values())
            if remaining > 0:
                order = sorted(eligible, key=lambda key: raw_add[key] - int(raw_add[key]), reverse=True)
                progressed = False
                for key in order:
                    if remaining == 0:
                        break
                    if quotas[key] < len(buckets[key]):
                        quotas[key] += 1
                        remaining -= 1
                        progressed = True
                if not progressed and remaining > 0:
                    raise SystemExit("Could not allocate remaining sample slots; reduce --n.")

    rng = random.Random(args.seed)
    chosen = []
    for band, n in quotas.items():
        chosen.extend(rng.sample(buckets[band], n))
    rng.shuffle(chosen)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in chosen:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    actual = Counter(row["length_band"] for row in chosen)
    print(f"Source={len(source)}; eligible={sum(map(len, buckets.values()))}; outside bands={outside}")
    print(f"Selected={len(chosen)}; seed={args.seed}; output={output}")
    if shortage:
        print("Quota shortages were redistributed. Interpret length-band results using the actual counts below.")
    for band, share in SHARES.items():
        print(f"{band}: {actual[band]}/{len(chosen)} = {actual[band]/len(chosen):.1%} (target {share:.0%})")


if __name__ == "__main__":
    main()
