"""Run the On This Day pipeline with a manually specified event.

Use this when you want to push a specific event to the display instead of
letting the automatic selector pick one. Edit YEAR and TEXT below, then run:

    python run_manual_event.py           # generate + post to TRMNL
    python run_manual_event.py --no-post # generate only (saves to output/latest.png)
"""
from __future__ import annotations

import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Edit these two values ────────────────────────────────────────────────────
YEAR = "1965"
TEXT = (
    "Martin Luther King Jr. leads 3,200 people on the start of the third and "
    "finally successful civil rights march from Selma to Montgomery, Alabama."
)
# ─────────────────────────────────────────────────────────────────────────────

no_post = "--no-post" in sys.argv

words = TEXT.split()
description = " ".join(words[:20])

from on_this_day.config import load_config
config = load_config()

logger.info("Event: [%s] %s", YEAR, TEXT)
logger.info("Description (20 words): %s", description)

logger.info("Generating image...")
t0 = time.time()
from on_this_day.generator import generate_image
raw_png = generate_image(TEXT, config.gemini_api_key)
if raw_png is None:
    logger.error("Image generation failed.")
    sys.exit(1)
logger.info("Image generated in %.1fs (%d bytes)", time.time() - t0, len(raw_png))

from on_this_day.composer import compose_image
final_png = compose_image(raw_png, YEAR, description)

output_dir = Path(__file__).parent / "output"
output_dir.mkdir(exist_ok=True)
(output_dir / "latest.png").write_bytes(final_png)
logger.info("Saved to output/latest.png")

if no_post:
    logger.info("--no-post flag set — skipping TRMNL webhook")
else:
    from on_this_day.poster import post_to_trmnl
    post_to_trmnl(final_png, config.trmnl_webhook_url)
    logger.info("Posted to TRMNL successfully")

    if config.discord_webhook_url:
        from on_this_day.discord import notify_success
        try:
            notify_success(config.discord_webhook_url, final_png, YEAR, description, [])
        except Exception as exc:
            logger.warning("Discord notification failed (non-fatal): %s", exc)
