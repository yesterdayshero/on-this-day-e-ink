# 📅 On This Day art for TRMNL e-ink display

A daily historical event display for TRMNL e-ink displays. Fetches today's most significant event from Wikipedia, generates a woodcut-style illustration via the Gemini API, and posts it to your TRMNL display.

<table>
  <tr>
    <td><img src="samples/woodcut/1638-calabrian-earthquakes.png" alt="Woodcut Style: 1638 Calabrian Earthquakes" width="400"></td>
    <td><img src="samples/sketch/1900-hieroglyphics.png" alt="Pencil Sketch Style: 1900 Hieroglyphics" width="400"></td>
  </tr>
</table>

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
# Edit .env and add your GEMINI_API_KEY and TRMNL_WEBHOOK_URL (See Environment variables section below for optional configurations)
uv sync
```

### 🚀 Run

```bash
uv run python -m on_this_day
```

Executes the full pipeline: fetches events, scores them, generates the image, and pushes it to your TRMNL display.

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
   - Program: `C:\path\to\your\.cargo\bin\uv.exe` (Ensure you use the absolute path to uv.exe, otherwise the task will fail silently. You can find this path by running `where uv` in Command Prompt.)
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
| `TIMEZONE` | No | Default: `UTC` (Make sure to set this to your local timezone using [tz database format](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) so your events trigger on the correct "today"!) |

> [!NOTE] 
> **API Costs 💸:** Gemini text models (used for scoring) have a generous free tier. However, the Gemini image generation model is a paid API. Generating one daily image will incur a very small monthly cost (typically a few cents per month). To optimise costs, you can provide a secondary free-tier `GEMINI_SCORING_API_KEY` to handle the text-heavy categorisation, reserving your paid `GEMINI_API_KEY` exclusively for the single final image generation.

## 🛠️ Development

### Run tests

```bash
uv run pytest
```

### 📁 Project structure

```
├── src/on_this_day/
│   ├── __main__.py   # entry point — orchestrates the full pipeline
│   ├── config.py     # loads .env, validates required vars
│   ├── fetcher.py    # Wikipedia REST API
│   ├── selector.py   # LLM-powered event scoring (Gemini 2.5 Flash); keyword fallback
│   ├── generator.py  # Gemini image generation (3.1 Flash Image)
│   ├── composer.py   # crop → posterise → text overlay
│   ├── poster.py     # TRMNL webhook upload
│   └── discord.py    # Discord webhook notifications
├── run_manual_event.py          # Utility: Push a specific event
├── extract_categorised_events.py # Utility: Test event selection & scoring
├── pyproject.toml               # uv project definitions
└── .env.example
```

## 📜 Logs

Rotating daily logs in `logs/app.log`. 30 days retained.

## 🖼️ Output

The last generated image is saved to `output/latest.png` for inspection.

## 🚑 Troubleshooting

- **Check the logs:** If something goes wrong, your first step should always be checking `logs/app.log`.
- **TRMNL Webhook Errors:**
  - `422 Unprocessable Entity`: Your image might be too large (over 5 MB), the wrong format, or corrupted. Try dropping it to a simple PNG.
  - `429 Too Many Requests`: You've hit the TRMNL rate limit (12 uploads per hour). Wait a bit before sending more.
- **Image pushes but display doesn't update:**
  - Check that your POST request returned a `200` response. You can also try the "Force Refresh" button in the plugin settings.
  - **Pro-tip:** In the TRMNL webhook plugin settings on the dashboard, try enabling **"Skip Device Validation"** if your image isn't rendering.
  - **Pro-tip:** For the best visual result, choose **"Contain"** for the image scaling option in the TRMNL plugin settings so the full image is shown.

## 📄 Licence

This project is licensed under the [Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0)](LICENSE).
