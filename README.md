# 📅 On This Day art for TRMNL e-ink display

A daily historical event display for TRMNL e-ink displays. Fetches today's most significant event from Wikipedia, generates a woodcut-style illustration via the Gemini API, and posts it to your TRMNL display.

## ⚙️ Setup

### ✅ Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
- Gemini API key
- TRMNL device with a **[Webhook Image (Experimental)](https://help.trmnl.com/en/articles/13213669-webhook-image-experimental)** plugin configured (create this in your TRMNL dashboard and copy the Webhook URL)

### ⬇️ Installation

```bash
git clone https://github.com/yesterdayshero/on-this-day-e-ink.git
cd on-this-day-e-ink
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY and TRMNL_WEBHOOK_URL
uv sync
```

### 🚀 Run manually

```bash
uv run python -m on_this_day
```

### 🧪 Test without posting to TRMNL

```bash
uv run python -m on_this_day --no-post
```

The generated image is saved to `output/latest.png` for inspection.

### 🎯 Push a specific event manually

Edit `YEAR` and `TEXT` at the top of `run_manual_event.py`, then:

```bash
# Preview only
uv run python run_manual_event.py --no-post

# Generate and post to TRMNL
uv run python run_manual_event.py
```

Use this when you want to override the automatic selector — e.g. to push a particular event that didn't get picked, or to test a specific date. The script bypasses fetching and scoring entirely and runs the rest of the pipeline (image generation, composition, TRMNL post, Discord notification) as normal.

## 🕒 Automation

### Linux & macOS (Cron)

The ideal way to run this on Linux or macOS is via a daily cron job. 

```bash
# Open crontab
crontab -e

# Add a job to run daily at 5:30 AM
30 5 * * * cd /path/to/on-this-day-e-ink && /home/user/.local/bin/uv run python -m on_this_day >> logs/cron.log 2>&1
```
*(Note for macOS users: You may need to grant 'Full Disk Access' to `cron` or `Terminal` in System Settings > Privacy & Security).*

### Windows Task Scheduler

1. Open **Task Scheduler** → **Create Basic Task**
2. Trigger: Daily at 5:30 AM
3. Action: Start a program
   - Program: `uv`
   - Arguments: `run python -m on_this_day`
   - Start in: `<path-to-project-folder>`
4. Confirm the task runs by triggering it manually.

## 🎛️ Tuning event selection

The selector uses Gemini Flash to categorise events and assigns points per category (`CATEGORY_POINTS` in `selector.py`). To tune it:

1. **Capture a real dataset** with the extraction utility:

   ```bash
   uv run python extract_categorised_events.py              # today's date
   uv run python extract_categorised_events.py --month 3 --day 21
   ```

   This fetches events, applies exclusion/dedup filters, calls Gemini for categorisation, and saves the result to `output/categorised_events.json`.

2. **Adjust scoring** in `src/on_this_day/selector.py`:
   - `CATEGORY_POINTS` — points per category
   - `LOCAL_KEYWORDS` — terms that add a local relevance bonus
   - `EXCLUSION_*` — events to skip entirely

3. **Re-run** `extract_categorised_events.py` against different dates to verify the changes behave as expected before deploying.

## 🔑 Environment variables & Cost

| Variable | Required | Purpose |
|----------|----------|---------|
| `GEMINI_API_KEY` | Yes | Paid key — image generation (+ scoring fallback) |
| `TRMNL_WEBHOOK_URL` | Yes | TRMNL display webhook |
| `GEMINI_SCORING_API_KEY` | No | Free-tier key — used for event categorisation to save cost |
| `DISCORD_WEBHOOK_URL` | No | Daily digest + failure alerts |
| `LOG_LEVEL` | No | Default: `INFO` |
| `TIMEZONE` | No | Default: `UTC` (Use [tz database format](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)) |

> [!NOTE] 
> **API Costs 💸:** Gemini text models (used for scoring) have a generous free tier. However, the Gemini image generation model is a paid API. Generating one daily image will incur a very small monthly cost (typically a few cents per month). To optimise costs, you can provide a secondary free-tier `GEMINI_SCORING_API_KEY` to handle the text-heavy categorisation, reserving your paid `GEMINI_API_KEY` exclusively for the single final image generation.

## 🛠️ Development

### Run tests

```bash
uv run pytest
```

### 📁 Project structure

```
src/on_this_day/
├── __main__.py   # entry point — orchestrates the full pipeline
├── config.py     # loads .env, validates required vars
├── fetcher.py    # Wikipedia REST API
├── selector.py   # LLM-powered event scoring (Gemini 2.5 Flash); keyword fallback
├── generator.py  # Gemini image generation (3.1 Flash Image)
├── composer.py   # crop → posterise → text overlay
├── poster.py     # TRMNL webhook upload
└── discord.py    # Discord webhook notifications
```

## 📜 Logs

Rotating daily logs in `logs/app.log`. 30 days retained.

## 🖼️ Output

The last generated image is saved to `output/latest.png` for inspection.
