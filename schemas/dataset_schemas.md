# Dataset schemas

## `selected_reviews.jsonl`
One JSON object per selected review. Preserves all original fields and adds:
- `review_id`: unique string; if absent, a source-order ID is generated.
- `word_count`: integer computed from review text.
- `length_band`: `short_51_99`, `medium_101_199`, or `long_200_300`.

Bands: 51–99 words; 101–199 words; 200–300 words inclusive. Other lengths are ineligible for this stratified sample. Defaults are n=130 and random seed=42. If a length band has fewer reviews than its target quota, available reviews in that band are retained and the shortfall is redistributed across eligible bands; `--strict-quotas` disables redistribution. The source corpus is never modified.

## `clauses.jsonl`
One JSON object per clause:
- `review_id`, `sentence_id`, `clause_id`: stable identifiers; `clause_id` is the join key.
- `review_text`, `sentence_text`, `clause_text`
- `previous_sentence`, `next_sentence`
- `clause_ports_detected`, `has_port_switch`: heuristic metadata from `utils.py`; do not treat these as human gold labels.
- `word_count`, `length_band` (copied from selected reviews where available).

Both methods must use the same clause IDs and boundaries. If segmentation changes, regenerate the clauses and re-check annotations.

## `annotation_template.csv`
One row per clause, with IDs/context plus blank annotation fields:
- `destination_label`: `Roatan`, `Costa Maya`, `Cozumel`, `multiple_destinations`, `general_cruise`, or `unclear`.
- `destination_set`: exact port names separated by `|` (e.g. `Roatan|Cozumel`); use for the relevant port(s).
- `sentiment_label`: `positive`, `negative`, `neutral`, or `mixed`.
- `evidence_type`: `explicit`, `contextual`, or `insufficient`.

After annotation and QA, save a copy as `gold_labels.csv`; keep the blank template unchanged.

## Deferred: `review_splits.csv`
Create only after gold labels are finalized. One row per review, with `review_id` and `split` (`train`, `validation`, `test`). Split by review ID, never by clause, and use the same held-out test reviews for both attribution methods.
