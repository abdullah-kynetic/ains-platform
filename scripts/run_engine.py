"""Run the rule-based engine over the synthetic firms and print scores. No model calls.

Usage: uv run python scripts/run_engine.py
"""

from audit_engine.collect import FIRMS_ROOT, collect_firm
from audit_engine.rules import run_rules
from audit_engine.scoring import declared_na, load_answer_key, score


def main() -> None:
    for folder in sorted(p for p in FIRMS_ROOT.iterdir() if p.is_dir()):
        key = load_answer_key(folder / "answer_key.json")
        collection = collect_firm(folder.name, declared_na(key))
        result = score(key, collection, run_rules(collection))
        print(
            f"{folder.name}: found {result.found}/{result.expected} "
            f"false+ {result.false_positives} missed {result.missed} "
            f"unexpected {result.unexpected}"
        )


if __name__ == "__main__":
    main()
