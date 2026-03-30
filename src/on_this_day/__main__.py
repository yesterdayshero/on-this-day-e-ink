from __future__ import annotations

import logging
import sys
import time
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def _setup_logging(log_level: str) -> None:
    logs_dir = Path(__file__).parent.parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    level = getattr(logging, log_level, logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)

    file_handler = TimedRotatingFileHandler(
        logs_dir / "app.log",
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)
    root.addHandler(console)
    root.addHandler(file_handler)


def main() -> None:
    no_post = "--no-post" in sys.argv

    # Bootstrap logging with INFO until config is loaded
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    logger = logging.getLogger(__name__)

    discord_url = ""
    try:
        from on_this_day.config import load_config
        config = load_config()
        discord_url = config.discord_webhook_url

        # Re-configure logging with correct level from config
        logging.getLogger().handlers.clear()
        _setup_logging(config.log_level)
        logger = logging.getLogger(__name__)

        logger.info("Starting On This Day — date: %s", config.today)

        from on_this_day.fetcher import fetch_events
        events = fetch_events(config.today.month, config.today.day)
        logger.info("Fetched %d events from Wikipedia", len(events))

        from on_this_day.selector import select_event
        best, runners_up = select_event(events, config.gemini_scoring_api_key)
        logger.info(
            "Selected: [%s] %s",
            best.get("year", "?"),
            best.get("text", "")[:80],
        )
        for i, r in enumerate(runners_up, 1):
            logger.info("  Runner-up #%d: [%s] %s", i, r.get("year", "?"), r.get("text", "")[:60])

        # Derive display fields from best event
        year = str(best.get("year", ""))
        text = best.get("text", "")

        from on_this_day.summariser import summarise_description
        description = summarise_description(text, config.gemini_scoring_api_key)

        # Build scene description for image prompt
        scene = text

        logger.info("Generating image for: %s", scene[:80])
        t0 = time.time()
        from on_this_day.generator import generate_image
        raw_png = generate_image(scene, config.gemini_api_key, style=config.image_style)
        if raw_png is None:
            raise RuntimeError("Image generation failed after all retries")
        logger.info("Image generated in %.1fs (%d bytes)", time.time() - t0, len(raw_png))

        from on_this_day.composer import compose_image
        final_png = compose_image(raw_png, year, description)

        # Save latest image for inspection
        output_dir = Path(__file__).parent.parent.parent / "output"
        output_dir.mkdir(exist_ok=True)
        (output_dir / "latest.png").write_bytes(final_png)
        logger.info("Saved to output/latest.png")

        if no_post:
            logger.info("--no-post flag set — skipping TRMNL webhook")
        else:
            from on_this_day.poster import post_to_trmnl
            post_to_trmnl(final_png, config.trmnl_webhook_url)
            logger.info("Posted to TRMNL successfully")

        # Discord digest
        if config.discord_webhook_url:
            from on_this_day.discord import notify_success
            try:
                notify_success(config.discord_webhook_url, final_png, year, description, runners_up)
            except Exception as disc_exc:
                logger.warning("Discord notification failed (non-fatal): %s", disc_exc)
        else:
            logger.debug("DISCORD_WEBHOOK_URL not set — skipping Discord notification")

    except Exception as exc:
        logging.getLogger(__name__).exception("Unhandled error: %s", exc)
        if discord_url:
            try:
                from on_this_day.discord import notify_failure
                notify_failure(discord_url, str(exc))
            except Exception:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()
