# Annotation guidelines

**Version 0.1 (draft).** These guidelines are based on the 27 clauses already
labeled in `data/annotations/annotated_reviews.csv` (reviews 498, 81 and 367).
Rules marked **[confirm]** are inferred from those labels or are proposed
defaults. Confirm or change them before annotating further.

## 1. Task

Each row of `annotation_template.csv` is one **clause** from a cruise review.
For every clause, record:

1. **which port** it is about (`destination_label`, `destination_set`),
2. **how the reviewer feels about it** (`sentiment_label`),
3. **how you know which port it is about** (`evidence_type`).

The labels are the gold standard for comparing automatic destination
attribution methods. The goal is to capture what the reviewer meant, not what
a keyword search would find.

The ports in scope are **Roatan**, **Costa Maya** and **Cozumel**.

## 2. General principles

- **Label the clause, read the context.** Each label describes `clause_text`
  only. Use `previous_sentence`, `sentence_text`, `next_sentence` and, when
  needed, the full review to work out what the clause refers to.
- **Don't fix segmentation.** If a clause boundary looks wrong, label the clause
  as given, and record the `clause_id` in a separate issues list for review.
  Never edit IDs, text or row order.
- **Don't use the hint fields.** `clause_ports_detected` and
  `has_port_switch` in `clauses.jsonl` come from keyword matching and are not
  in the annotation template. Don't use them as evidence.
- **When in doubt, pick the more conservative label** (`unclear`,
  `neutral`, `insufficient`) rather than guessing.

## 3. Destination

### 3.1 `destination_label`

| Value | Use when | Example (from this dataset) |
|---|---|---|
| `Roatan` / `Costa Maya` / `Cozumel` | The clause is about one port. | "Roatan was a bit harder to do alone as the taxis are expensive for one person." → `Roatan` |
| `multiple_destinations` | The clause evaluates or compares two or more in-scope ports. | "The reef there [Roatan] is in much better shape than Cozumel." → `multiple_destinations` |
| `general_cruise` | The clause is about the cruise as a whole and not a specific port: the ship, the itinerary overall, embarkation, onboard food, cabins, the cruise line. | "Overall, the itinerary felt a bit uneven," → `general_cruise` |
| `unclear` | A port may be meant, but even with context you can't tell which, or whether it is about a port at all. | |

Write port names exactly as shown: `Roatan` (no accent), `Costa Maya`,
`Cozumel`. All other values are lowercase with underscores.

### 3.2 `destination_set`

Lists the specific port(s) the clause refers to, separated by `|` with no
spaces, in any order:

| `destination_label` | `destination_set` |
|---|---|
| single port | the same port, e.g. `Cozumel` |
| `multiple_destinations` | every port involved, e.g. `Roatan\|Cozumel` |
| `general_cruise` | blank |
| `unclear` | blank, or the candidate ports if you can narrow it down **[confirm]** |

### 3.3 Carrying a port forward from context

Reviews usually name a port once and then keep talking about it. A clause
**without** a port name takes the most recently established port, as long as
it plausibly continues that topic. The carry-over ends when the reviewer:

- names a different port,
- moves to the cruise in general ("Overall…", "The ship…"), or
- clearly changes subject.

Examples from review 498:

> "I'm a solo traveler and found **Cozumel** very easy to navigate." → `Cozumel`
> "I just rented a scooter and rode around the island." → `Cozumel` (carried)
> "The east side is deserted and beautiful." → `Cozumel` (carried)
> "**Roatan** was a bit harder to do alone…" → `Roatan` (switch)
> "I ended up joining a group for a snorkeling trip." → `Roatan` (carried)

### 3.4 Place names that indicate a port

Count these as naming the port (`explicit`):

| Port | Also indicated by |
|---|---|
| Roatan | West End, West Bay, Coxen Hole, Mahogany Bay, "Honduras" (when only Roatan fits) |
| Costa Maya | Mahahual / the Malecón in Mahahual |
| Cozumel | San Gervasio, San Miguel |

"Mexico" alone could mean Cozumel or Costa Maya. Use the context. If it
clearly covers both ("both Mexico stops"), use `multiple_destinations` with
`Costa Maya|Cozumel`. **[confirm]**

Other places, such as other ports, the home port or "the Caribbean", aren't in
scope. Label the clause by what it says about the in-scope ports or the
cruise, or use `unclear`.

### 3.5 Edge cases

- **Comparisons between ports** → `multiple_destinations`, listing every port
  compared, even if the clause is mostly about one of them.
  "I'd say Cozumel works best for casual exploring while Roatan is better for
  planned activities." → `multiple_destinations`, `Roatan|Cozumel`.
- **Time spread across ports** ("Costa Maya having more time than we needed
  and Cozumel not quite enough") → `multiple_destinations`.
- **Staying on the ship while in port** ("In Costa Maya, we decided to stay on
  the ship…") → the port, because the clause is about the port.
- **Onboard experience not tied to a port** (food, cabins, staff, shows) →
  `general_cruise`.
- **Logistics tied to a port** (tendering in Cozumel, the pier in Roatan,
  all-aboard time after a Roatan excursion) → that port.
- **Excursion companies or guides** → the port where the excursion took place.

## 4. Sentiment

### 4.1 `sentiment_label`

Sentiment is the reviewer's attitude toward the destination(s) in
`destination_label`, as expressed **in this clause**.

| Value | Use when | Example |
|---|---|---|
| `positive` | Approval, enjoyment, recommendation, praise, including mild praise ("fine", "decent", "okay") | "The port area is fine" → `positive` |
| `negative` | Criticism, disappointment, complaint, warning | "but everything is priced for tourists." → `negative` |
| `neutral` | A factual or descriptive statement with no evaluation | "I ended up joining a group for a snorkeling trip." → `neutral` |
| `mixed` | Positive and negative judgments in the same clause, or opposite judgments of different ports | "The reef there is in much better shape than Cozumel." → `mixed` |

### 4.2 Rules

- **Mild words count.** "Fine", "decent", "okay" and "still decent" are
  `positive`. "A bit" or "slightly" before a negative word is still
  `negative`. **[confirm]** Under this rule, "Cozumel was okay" is positive.
- **Facts are neutral unless they are clearly evaluative.** "We did a
  two-tank dive and saw a few reef sharks and a massive grouper" was labeled
  `positive` because, for a diver, seeing sharks and a grouper is a highlight.
  "I just rented a scooter" is `neutral`. Choose `positive` or `negative` only
  when a typical reader would see the statement as good or bad.
- **Implied sentiment.** You can use context to read tone, but don't carry
  sentiment over from a neighboring clause. In "Cozumel was enjoyable but
  crowded," the first clause is `positive` and "but crowded." is `negative`.
- **Contrast clauses are judged separately.** The splitter puts "but …" into
  its own clause, and each part gets its own sentiment.
- **Comparisons.** If the comparison favors one port over another, use
  `mixed`, since one port is judged better and the other worse. If both ports
  are praised ("Roatan is a must, but Cozumel is still decent"), the clause is
  split, and each part is labeled on its own.
- **Choices that imply a judgment.** "For Costa Maya, I decided to just relax"
  was labeled `positive`. **[confirm]** This reads as the reviewer enjoying a
  relaxing day; if you didn't intend that, a stricter reading would make it
  `neutral`. Decide one way and apply it consistently.
- **Sarcasm and hedging.** Label the meaning the reviewer intends, not the
  literal words.

## 5. Evidence type

### 5.1 `evidence_type`

| Value | Use when | Example |
|---|---|---|
| `explicit` | Every port in `destination_set` is named in the clause itself, including by an alias in §3.4. For `general_cruise`, the clause itself clearly refers to the cruise, ship or itinerary. | "Roatan ended up being the highlight for us." |
| `contextual` | At least one port is inferred from surrounding text: carried forward, a pronoun ("there", "it"), or "the island", "the port". | "The east side is deserted and beautiful." (Cozumel, from the previous sentence) |
| `insufficient` | Even with the context, there isn't enough to say what the clause is about. Normally paired with `unclear`. | |

For `multiple_destinations`, if any port is inferred, the clause is
`contextual`. Example: "The reef **there** is in much better shape than
Cozumel" names Cozumel, but Roatan comes from "there".

## 6. Fragments and segmentation problems

Clause splitting produces short fragments.

- **A fragment with evaluative content** ("but crowded.", "but very
  expensive.") → label it normally, taking the port from context. Evidence is
  usually `contextual`.
- **A fragment with no content of its own** (e.g. "yet.", caused by a known
  splitter bug) → `unclear`, `neutral`, `insufficient`, and note the
  `clause_id` in the issues list. **[confirm]**
- **A clause that should have been split** (e.g. two ports with different
  sentiment in one clause) → label it as a whole, using
  `multiple_destinations` / `mixed` where that applies, and note it in the
  issues list.

## 7. Quick decision guide

1. Is the clause about the cruise/ship as a whole? → `general_cruise`, blank
   set. Go to step 4.
2. Which in-scope ports does it evaluate or describe, named or carried over
   from context?
   - none can be determined → `unclear`
   - one → that port
   - two or more → `multiple_destinations`
3. Fill in `destination_set` to match.
4. Sentiment toward those destinations in this clause →
   `positive` / `negative` / `neutral` / `mixed`.
5. Is every port named in the clause? → `explicit`. If any is inferred →
   `contextual`. If you can't tell → `insufficient`.

## 8. Quality control

- **Leave no blanks.** Every row needs `destination_label`, `sentiment_label`
  and `evidence_type`. `destination_set` stays blank only for
  `general_cruise` (and possibly `unclear`).
- **Use the exact label values.** Use the values in §3–5 exactly; they are
  case-sensitive. Before freezing, validate the file, e.g.:

  ```python
  import pandas as pd
  df = pd.read_csv("data/annotations/gold_labels.csv", encoding="utf-8-sig", dtype=str)
  allowed = {
      "destination_label": {"Roatan", "Costa Maya", "Cozumel",
                            "multiple_destinations", "general_cruise", "unclear"},
      "sentiment_label": {"positive", "negative", "neutral", "mixed"},
      "evidence_type": {"explicit", "contextual", "insufficient"},
  }
  for col, ok in allowed.items():
      bad = df[~df[col].isin(ok)]
      print(col, "invalid rows:", len(bad))
  ```

- **Measure agreement.** Have a second annotator label a sample of at least
  15–20 reviews, covering every clause in each. Compute Cohen's kappa for each
  label column. Resolve disagreements by discussion, and update these
  guidelines whenever a new rule comes out of that.
- **Freeze the labels.** Once QA is done, save the final file as
  `data/annotations/gold_labels.csv`, increase the version number at the top
  of this document, and don't change either afterwards without a recorded
  reason.

## Changelog

- **0.1:** First draft, based on the labels for reviews 498, 81 and 367.
