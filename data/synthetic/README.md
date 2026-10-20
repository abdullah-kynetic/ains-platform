# Synthetic data only

Only **fake** documents belong here: made-up firms, people, account numbers, and transactions created for tests and demos.

- Never place real client documents, real names, or anything copied from an engagement here.
- No real SARs. Synthetic "SAR-like" files exist only to prove they are blocked from AI.
- Real data, if ever needed locally, goes in `data/real/` (git-ignored) and never into AI tools without approval.

## Evaluation set

`manifest.json` defines seven expected status decisions: clean, missing, wrong period, bad scan,
partial, planted SAR, and prompt injection. Run the credential-free routing baseline with:

```bash
uv run python scripts/evaluate_synthetic.py
```

The planted SAR case must report `ai_called=false`. To measure a configured provider against the
same fully synthetic set, use `--provider anthropic` or `--provider openai`. The evaluator reads
provider credentials from process environment variables only; it does not load `.env`. Live-mode
scores measure model behavior and may differ from the deterministic offline baseline.
