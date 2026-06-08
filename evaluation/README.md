# Identification Evaluation

Create `evaluation/manifest.csv` with at least 20 real, consented outdoor-garden
examples. Use one to three image paths separated by `|` in the `images` column.

Run the live Modal evaluation:

```bash
MODAL_ENDPOINT=... MODAL_KEY=... MODAL_SECRET=... \
  uv run python scripts/evaluate.py evaluation/manifest.csv
```

The report contains species top-1, species top-3, genus top-1, per-case
predictions, and latency. Do not publish photographs, usernames, or precise
locations without explicit consent.

