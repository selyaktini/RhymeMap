"""Download the NLTK corpora g2p_en needs.

g2p_en loads CMUdict and a POS tagger through NLTK, but installs no data.
Without this step the first out-of-vocabulary word raises LookupError, which
used to surface as an unexplained crash partway through a run.
"""

from __future__ import annotations

import sys

RESOURCES = ["cmudict", "averaged_perceptron_tagger", "averaged_perceptron_tagger_eng"]


def main() -> int:
    try:
        import nltk
    except ImportError:
        print("nltk is not installed; run `pip install -r requirements.txt` first.", file=sys.stderr)
        return 1

    failed = []
    for resource in RESOURCES:
        try:
            if not nltk.download(resource, quiet=True):
                failed.append(resource)
        except Exception as exc:
            print(f"  {resource}: {type(exc).__name__}: {exc}")
            failed.append(resource)

    if failed:
        print(f"could not download: {', '.join(failed)}")
        print("RhymeMapper still runs; only out-of-vocabulary words will be affected.")
        print("Retry later with: python -m scripts.fetch_nltk_data")
        return 0     # not fatal: dictionary words work without it

    print(f"NLTK data ready ({', '.join(RESOURCES)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
