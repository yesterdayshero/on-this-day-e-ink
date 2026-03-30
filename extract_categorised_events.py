"""
Dev utility: fetch On This Day events for a given date, run Gemini categorisation,
and save the results to output/categorised_events.json for local testing.

Use this whenever you want to inspect or tune the selection criteria — run it first
to capture a real categorised dataset, then adjust selector.py and re-score locally.

Usage (from project root):
    uv run python extract_categorised_events.py              # today's date
    uv run python extract_categorised_events.py --month 3 --day 21
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

# Add src to path so we can import the package without installing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from on_this_day.fetcher import fetch_events
from on_this_day.selector import (
    _categorise_with_gemini,
    _deduplicate_overlap,
    _is_excluded,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", type=int, default=date.today().month)
    parser.add_argument("--day", type=int, default=date.today().day)
    args = parser.parse_args()

    load_dotenv()
    api_key = os.environ.get("GEMINI_SCORING_API_KEY", "").strip()
    if not api_key:
        sys.exit("GEMINI_SCORING_API_KEY not set in .env")

    logger.info("Fetching events for %02d-%02d ...", args.month, args.day)
    raw_events = fetch_events(args.month, args.day)
    logger.info("Fetched %d raw events", len(raw_events))

    eligible = [e for e in raw_events if not _is_excluded(e)]
    logger.info("%d events after exclusion filter", len(eligible))

    eligible = _deduplicate_overlap(eligible)
    logger.info("%d events after deduplication", len(eligible))

    logger.info("Calling Gemini for categorisation (%d events) ...", len(eligible))
    categories_list = _categorise_with_gemini(eligible, api_key)

    results = []
    for event, categories in zip(eligible, categories_list):
        results.append({
            "year": event.get("year"),
            "text": event.get("text", ""),
            "pages": [p.get("title") for p in event.get("pages", [])],
            "categories": categories,
        })

    out_dir = Path(__file__).parent / "output"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "categorised_events.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info("Saved %d categorised events to %s", len(results), out_path)
    print(f"\nDone. Results saved to: {out_path}")


if __name__ == "__main__":
    main()
