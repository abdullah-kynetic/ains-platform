# Synthetic data only

Only **fake** documents belong here: made-up firms, people, account numbers, and transactions created for tests and demos.

- Never place real client documents, real names, or anything copied from an engagement here.
- No restricted-content records or fixtures. No real client documents anywhere in this checkout.

## Evaluation set

`manifest.json` defines six upload-only cases: clean, missing, wrong period, invalid image,
partial, and untrusted text. Run the credential-free validation with:

```bash
uv run python scripts/evaluate_synthetic.py
```

Receiving a file is not an audit decision. Wrong-period and partial examples can be received;
the auditor later assesses them. There are no model calls, provider options, or real documents.
