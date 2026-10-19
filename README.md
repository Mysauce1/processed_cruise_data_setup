# Cruise review dataset setup

Builds a reproducible, **clause-level gold-standard dataset** for studying how
sentiment in cruise reviews attaches to specific ports of call (Roatan,
Costa Maya and Cozumel).

A single review often covers several ports, as in *"Roatan was the highlight,
but Costa Maya felt manufactured."* Review-level sentiment can't say which port
a comment is about. This repo:

1. draws a length-stratified random sample of reviews,
2. splits each review into sentences and clauses with stable IDs,
3. produces a blank CSV for annotators to label each clause with its
   destination, sentiment and evidence type.

The resulting gold labels are the shared benchmark for comparing destination
attribution methods. Every method must be scored against the same clause
boundaries and IDs.

## Repository layout

```
.
├── README.md
├── ANNOTATION_GUIDELINES.md          # how to choose each label, with examples
├── requirements.txt
├── schemas/
│   └── dataset_schemas.md          # field-level schema for every dataset file
├── src/
│   ├── utils.py                    # shared loading, cleaning, port detection, sentence/clause splitting, VADER
│   ├── sample_reviews.py           # step 1: stratified sample
│   ├── build_clauses.py            # step 2: clause-level rows
│   └── make_annotation_template.py # step 3: blank annotation CSV
└── data/
    ├── raw/cruise_reviews.jsonl            # source corpus (600 reviews), never modified
    ├── processed/selected_reviews.jsonl    # output of step 1 (130 reviews)
    ├── processed/clauses.jsonl             # output of step 2 (1,233 clauses)
    ├── annotations/annotation_template.csv # output of step 3 (blank, keep unchanged)
    ├── annotations/annotated_reviews.csv   # annotation in progress (see "Project status")
    └── spacy_diagnostic_explainer/         # standalone tool explaining the "and"-split rule
```

## Requirements

- Python 3.10 or newer (tested on 3.11 and 3.13)
- The packages in `requirements.txt`: pandas, spaCy 3.x, ftfy, vaderSentiment
- spaCy's English model, `en_core_web_sm`

## Setup

```bash
git clone <repo-url> cruise_dataset_setup
cd cruise_dataset_setup

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Quick check that everything is installed:

```bash
python -c "import sys; sys.path.insert(0, 'src'); from utils import split_clauses; print(split_clauses('Roatan was great but Cozumel was crowded.'))"
```

## Usage

Run every command **from the repository root**. Each script also has the
paths below as its defaults, so `python src/<script>.py` with no arguments does
the same thing.

### 1. Sample reviews

```bash
python src/sample_reviews.py \
  --input data/raw/cruise_reviews.jsonl \
  --output data/processed/selected_reviews.jsonl \
  --n 130 --seed 42
```

Draws a random sample, without replacement, stratified by word count:

| Band             | Words   | Target share |
|------------------|---------|--------------|
| `medium_101_199` | 101–199 | 60%          |
| `short_51_99`    | 51–99   | 35%          |
| `long_200_300`   | 200–300 | 5%           |

Reviews outside these bands (≤50, exactly 100, or >300 words) are ineligible.
If a band has too few reviews, all of them are kept and the shortfall goes to
the other bands in proportion to their target shares. Add `--strict-quotas` to
stop with an error instead.

With the included corpus and seed 42, the expected output is:

```
Source=600; eligible=456; outside bands=144
Selected=130; seed=42; output=data/processed/selected_reviews.jsonl
Quota shortages were redistributed. Interpret length-band results using the actual counts below.
medium_101_199: 81/130 = 62.3% (target 60%)
short_51_99: 47/130 = 36.2% (target 35%)
long_200_300: 2/130 = 1.5% (target 5%)
```

The corpus has only 2 reviews in the long band, so report the actual band
proportions rather than the targets.

### 2. Build clause-level rows

```bash
python src/build_clauses.py \
  --input data/processed/selected_reviews.jsonl \
  --output data/processed/clauses.jsonl
```

Expected: `Reviews processed=130; clause rows=1233`.

Each review is split into sentences with spaCy, and each sentence into
clauses:

- **Contrast markers.** Text is split before `but`, `however` and `yet`, and
  the marker stays at the start of the following clause. `although` is
  deliberately **not** split, because it usually introduces a subordinate
  clause.
- **Independent "and" clauses.** Text is split at `and` only when spaCy finds
  that the second conjunct has its own subject. Lists ("turtles and rays") and
  adjective pairs ("short and smooth") are left whole. See *Known issues*: this
  rule currently fires far less often than intended.

IDs are hierarchical and stable: `review_id` → `{review_id}-S{nnn}` →
`{review_id}-S{nnn}-C{nn}`. `clause_id` is the join key for everything
downstream. Each row also includes the previous and next sentence for context,
plus heuristic port-detection fields (`clause_ports_detected`,
`has_port_switch`). These fields are **hints, not gold labels**.

### 3. Create the annotation template

```bash
python src/make_annotation_template.py \
  --input data/processed/clauses.jsonl \
  --output data/annotations/annotation_template.csv
```

This writes one row per clause with blank label columns. The file is UTF-8
with a BOM so Excel opens it correctly.

### Determinism

With the same input file, `--seed` and spaCy model version, the pipeline
reproduces the committed outputs exactly. This was verified with spaCy 3.8 and
`en_core_web_sm` 3.8.0. A different spaCy model version can change sentence and
clause boundaries, so record the version you used:

```bash
python -m spacy info en_core_web_sm | grep -i version
```

## Data flow

```
data/raw/cruise_reviews.jsonl
  → data/processed/selected_reviews.jsonl     (step 1)
  → data/processed/clauses.jsonl              (step 2)
  → data/annotations/annotation_template.csv  (step 3)
  → gold_labels.csv                           (human annotation + QA)
  → review_splits.csv                         (deferred, see below)
```

Full field definitions are in [`schemas/dataset_schemas.md`](schemas/dataset_schemas.md).

### Input format

`data/raw/cruise_reviews.jsonl` contains one JSON object per line. Each object
needs a non-empty string `review` field. A unique `review_id` is recommended;
if it's missing, an ID is generated from the review's position in the file.
All original fields are carried through.

The loader cleans text with `ftfy`, flattens newlines and normalizes smart
quotes and dashes. It also tries to recover malformed lines. One line in the
included corpus (line 121, which has unescaped quotes) is recovered this way.
Watch the console for any `Skipping bad line N` messages.

## Annotation guide

The full rules, with worked examples and edge cases, are in
[`ANNOTATION_GUIDELINES.md`](ANNOTATION_GUIDELINES.md). In summary, fill in
these columns for every clause:

| Column              | Allowed values |
|---------------------|----------------|
| `destination_label` | `Roatan`, `Costa Maya`, `Cozumel`, `multiple_destinations`, `general_cruise`, `unclear` |
| `destination_set`   | Exact port names separated by `\|`, e.g. `Roatan\|Cozumel` |
| `sentiment_label`   | `positive`, `negative`, `neutral`, `mixed` |
| `evidence_type`     | `explicit` (port named in the clause), `contextual` (port inferred from surrounding text), `insufficient` |

Rules:

- Keep `annotation_template.csv` blank. Annotate a copy, and save the final,
  QA'd version as `data/annotations/gold_labels.csv`.
- Never edit `review_id`, `sentence_id`, `clause_id` or `clause_text`, and
  don't add, delete or reorder rows.
- Use the exact spellings above. Label values are case-sensitive.
- Before annotation starts, review a sample of clauses. If segmentation
  changes after annotation has begun, regenerate `clauses.jsonl` and the
  template, then re-check any existing labels against the new `clause_id`s.

### Train / validation / test split (deferred)

Create `review_splits.csv` only after the gold labels are frozen. Assign one
split per `review_id`, keeping all clauses from a review in the same split.
Use the same held-out test reviews for every attribution method.

## Project status

- Steps 1–3 are complete. The committed outputs match a fresh run.
- Annotation has started. `data/annotations/annotated_reviews.csv` has labels
  for 27 clauses from 3 reviews (498, 81, 367). This file does **not** yet
  follow the schema:
  - Labels are in Title Case (`Positive`, `General Cruise`,
    `Multiple Destinations`) rather than the schema values (`positive`,
    `general_cruise`, `multiple_destinations`).
  - `destination_set` uses `, ` instead of `|` as the separator.

  Normalize these before the file becomes `gold_labels.csv`.

## Known issues

- **The "and"-split rule under-fires.** The rule checks whether the `and`
  token's head is labeled `conj`. In spaCy's parse, though, `cc` attaches to
  the *first* conjunct, which is usually the `ROOT`. As a result, the rule
  splits only 14 of the 1,031 sampled sentences. A corrected check (look for a
  `conj` child of the head that has its own subject) would split about 117
  sentences. That includes this repo's own example, "The boat ride was short
  and smooth, **and** we had plenty of time…", which currently stays one
  clause. Fixing the rule changes `clause_id`s, so decide on it **before**
  annotation goes further. The tool in `data/spacy_diagnostic_explainer/`
  shows the parse for this case.
- **`yet` as an adverb.** The contrast rule also splits on "yet" meaning "so
  far". For example, "…and nothing was open yet." produces a clause that is
  just `yet.`.
- Clause splitting is a heuristic, not a full clause parser. It produces short
  fragments such as `but crowded.`, which is intended: annotators should use
  `sentence_text` and the neighboring sentences for context.

## Utilities in `src/utils.py`

| Function | Purpose |
|----------|---------|
| `load_jsonl(path)` | Load JSONL into a DataFrame, clean the review text and recover malformed lines |
| `clean_text(text)` / `normalize_text(text)` | Fix encoding and normalize punctuation / lowercase for matching |
| `detect_ports(text)` | Return port names found in the text, in a fixed order |
| `split_sentences(text)` | Sentence split with spaCy (model loaded lazily) |
| `split_clauses(sentence)` | Clause split, with per-clause port hints |
| `get_sentiment(text)` | VADER compound score from −1 to +1 (not used by the pipeline; available for baselines) |

## Data source and license

<!-- TODO: say where cruise_reviews.jsonl came from (collected, scraped, synthetic?),
     any terms of use, and add a LICENSE file for the code. -->
_To be completed: document the provenance of `cruise_reviews.jsonl` and the
license for the code and data._
