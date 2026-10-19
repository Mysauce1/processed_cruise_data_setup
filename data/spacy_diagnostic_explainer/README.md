# spaCy diagnostic dataset generator

This package creates a CSV with spaCy's actual token-level dependency output for the two example sentences, plus extra columns that explain how each token fares against the project's `and`-splitting checks.

## Run it

In the Python environment used for your project:

From the repository root, with the project environment already set up (see the main README):

```bash
cd data/spacy_diagnostic_explainer
python make_diagnostic_dataset.py
```

The script writes its CSVs to the current directory, so run it from this folder to refresh the copies here.

It creates (committed copies are in this folder):

- `spacy_diagnostic_output.csv` — one row per token, including spaCy's actual `dep`, `head`, and `pos` values, character offsets, the split-check results, and a plain-English interpretation.
- `spacy_diagnostic_column_guide.csv` — a short explanation of each column.

The dependency parse is intentionally generated at runtime rather than filled in with guessed values. spaCy's exact parse can vary by model version, so this keeps the diagnostic tied to the model in your project environment.

The `would_append_boundary` column reports whether the token passes the checks in the shown code block. It does not guarantee that the resulting split is linguistically perfect.
