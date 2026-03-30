from __future__ import annotations

import json
import logging
import re

import requests

logger = logging.getLogger(__name__)

# ── Exclusion lists ────────────────────────────────────────────────────────────

EXCLUSION_ATROCITY_KEYWORDS = [
    "genocide", "ethnic cleansing", "mass execution", "death camp",
    "concentration camp", "extermination",
]

EXCLUSION_SAFETY_KEYWORDS = [
    "child abuse", "sexual assault", "rape",
]

BIRTH_DEATH_PATTERNS = [
    "was born", "born on this day", "died on this day", "passed away",
    "(born ", "died ",
]

GLOBAL_ICONS = [
    "Shakespeare", "Mozart", "Einstein", "Darwin", "Newton", "Curie",
    "Lincoln", "Churchill", "Gandhi", "Mandela", "Washington", "Napoleon",
    "Michelangelo", "da Vinci", "Beethoven", "Marx",
]

# ── Local relevance (Customize these for your region) ──────────────────────────

LOCAL_KEYWORDS = [
    "Australia", "Australian",
]

# ── Category scoring ──────────────────────────────────────────────────────────

CATEGORY_POINTS = {
    "scientific_breakthrough": 5,
    "transformative_invention": 5,
    "iconic_first": 4,
    "medical_breakthrough": 4,
    "historical_significance": 3,
    "disaster": 3,
    "terrorism_major_attack": 3,
    "sport_milestone": 3,
    "major_political_turning_point": 2,
    "war_battle": 2,
    "founding_of_major_institution": 2,
    "political_succession": 2,
    "cultural_milestone": 2,
    "treaty_diplomatic_milestone": 2,
    "natural_phenomenon": 2,
}

CATEGORY_NAMES = list(CATEGORY_POINTS.keys())

# ── Gemini categorisation ─────────────────────────────────────────────────────

_GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.5-flash:generateContent?key={api_key}"
)

_DEDUP_PROMPT = """\
You are a historian. The following events all occurred on the same date. Some entries describe \
the SAME historical occurrence in different words.

Group events that refer to the same occurrence. Return ONLY a JSON array of integers, one per \
event, where events sharing the same number are duplicates of each other. Use 0-based group IDs \
starting from 0, incrementing for each new unique event.

Example — if events 0 and 3 are the same, and events 1 and 2 are the same:
[0, 1, 1, 0]

Events:
{events_json}
"""

_CATEGORISATION_PROMPT = """\
You are a historian. For each event below, assign ALL categories that apply from this list:

- scientific_breakthrough: major scientific discoveries or publications (e.g. theory of relativity, discovery of DNA)
- transformative_invention: the creation or first demonstration of a wholly new technology that \
fundamentally changed society (e.g. printing press, telephone, internet). Do NOT apply to the \
first deployment or adoption of an existing technology.
- iconic_first: first-ever achievements (e.g. first flight, first broadcast, first voyage)
- major_political_turning_point: revolutions, declarations of independence, assassinations, coups, treaties
- medical_breakthrough: landmark medical treatments, drug approvals, vaccines, public health milestones
- historical_significance: events that fundamentally shaped civilisation or altered the course of history
- war_battle: wars, battles, invasions, sieges, military operations
- disaster: earthquakes, eruptions, tsunamis, shipwrecks, epidemics
- terrorism_major_attack: terrorist attacks, mass casualty attacks, politically motivated violence against civilians
- founding_of_major_institution: establishment of significant organisations, companies, or institutions
- political_succession: coronations, elections, inaugurations, abdications
- cultural_milestone: publications, premieres, releases, cultural achievements
- treaty_diplomatic_milestone: major treaties, international agreements, diplomatic breakthroughs
- natural_phenomenon: solar eclipses, rare astronomical events, non-destructive natural occurrences
- sport_milestone: landmark sporting events — first Olympics, inaugural World Cups, record-breaking achievements, historic firsts in sport

An event can belong to MULTIPLE categories or NONE.

Return ONLY a JSON array of arrays, one inner array per event, containing the category strings \
that apply. Use an empty array [] if no categories apply. No explanation.

Events:
{events_json}
"""


def _categorise_with_gemini(events: list[dict], api_key: str) -> list[list[str]]:
    """Call Gemini Flash to categorise events."""
    events_for_prompt = [
        {"year": e.get("year", "?"), "text": e.get("text", "")}
        for e in events
    ]
    prompt = _CATEGORISATION_PROMPT.format(events_json=json.dumps(events_for_prompt))

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
        # If categorisation quality remains poor, consider enabling thinking mode:
        # "generationConfig": {"temperature": 1.0, "thinkingConfig": {"thinkingBudget": 1024}},
        # Note: thinking mode requires temperature >= 1.0 and adds latency/cost.
    }

    response = requests.post(
        _GEMINI_API_URL.format(api_key=api_key),
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=120,
    )
    response.raise_for_status()

    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]

    # Extract JSON array from response (may be wrapped in markdown code block)
    match = re.search(r"\[[\s\S]*\]", text)
    if not match:
        raise ValueError(f"Could not parse categories from Gemini response: {text[:200]}")

    result = json.loads(match.group())

    # Handle minor count mismatches
    if len(result) < len(events):
        logger.warning("Gemini returned %d category sets for %d events — padding with empty", len(result), len(events))
        result.extend([[]] * (len(events) - len(result)))
    elif len(result) > len(events):
        logger.warning("Gemini returned %d category sets for %d events — truncating", len(result), len(events))
        result = result[:len(events)]

    # Filter out any invalid category names
    valid = set(CATEGORY_NAMES)
    return [[c for c in cats if c in valid] for cats in result]


def _calculate_score(categories: list[str], text: str) -> int:
    """Sum points from matched categories plus local relevance."""
    score = sum(CATEGORY_POINTS.get(c, 0) for c in categories)
    if any(kw in text for kw in LOCAL_KEYWORDS):
        score += 2
    return score


# ── Exclusion ──────────────────────────────────────────────────────────────────

def _is_excluded(event: dict) -> bool:
    text = event.get("text", "")
    text_lower = text.lower()

    for kw in EXCLUSION_ATROCITY_KEYWORDS + EXCLUSION_SAFETY_KEYWORDS:
        if kw in text_lower:
            return True

    is_birth_death = any(pattern in text_lower for pattern in BIRTH_DEATH_PATTERNS)
    if is_birth_death:
        is_iconic = any(icon in text for icon in GLOBAL_ICONS)
        if not is_iconic:
            return True

    return False


# ── Deduplication ──────────────────────────────────────────────────────────────

def _deduplicate_overlap(events: list[dict], threshold: float = 0.7) -> list[dict]:
    """Remove near-duplicate events based on word overlap ratio."""
    kept: list[dict] = []
    for e in events:
        words_e = set(e.get("text", "").lower().split())
        is_dup = False
        for k in kept:
            words_k = set(k.get("text", "").lower().split())
            if not words_e or not words_k:
                continue
            overlap = len(words_e & words_k) / min(len(words_e), len(words_k))
            if overlap >= threshold:
                is_dup = True
                logger.debug("Dedup: removed '%s' (%.0f%% overlap)", e.get("text", "")[:60], overlap * 100)
                break
        if not is_dup:
            kept.append(e)
    return kept


def _deduplicate_semantic(events: list[dict], api_key: str) -> list[dict]:
    """Use Gemini Flash to identify semantically duplicate events."""
    if len(events) <= 1:
        return events

    events_for_prompt = [
        {"year": e.get("year", "?"), "text": e.get("text", "")}
        for e in events
    ]
    prompt = _DEDUP_PROMPT.format(events_json=json.dumps(events_for_prompt))

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0},
    }

    response = requests.post(
        _GEMINI_API_URL.format(api_key=api_key),
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    response.raise_for_status()

    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]

    match = re.search(r"\[[\s\S]*?\]", text)
    if not match:
        raise ValueError(f"Could not parse dedup groups from Gemini response: {text[:200]}")

    groups = json.loads(match.group())

    if len(groups) != len(events):
        logger.warning(
            "Gemini returned %d group IDs for %d events — skipping semantic dedup",
            len(groups), len(events),
        )
        return events

    # Keep the longest description from each group (more detail = better)
    best_per_group: dict[int, dict] = {}
    for group_id, event in zip(groups, events):
        if group_id not in best_per_group:
            best_per_group[group_id] = event
        else:
            existing = best_per_group[group_id]
            if len(event.get("text", "")) > len(existing.get("text", "")):
                best_per_group[group_id] = event

    kept = list(best_per_group.values())
    removed = len(events) - len(kept)
    if removed:
        logger.info("Semantic dedup removed %d duplicate(s), %d events remain", removed, len(kept))
    return kept


def _deduplicate_topics(ranked: list[dict]) -> list[dict]:
    """Keep only the highest-scoring event per colon-prefixed topic."""
    seen_topics: set[str] = set()
    result: list[dict] = []
    for event in ranked:
        text = event.get("text", "")
        if ": " in text:
            topic = text.split(": ", 1)[0].strip().lower()
            if topic in seen_topics:
                continue
            seen_topics.add(topic)
        result.append(event)
    return result


# ── Scoring helpers ────────────────────────────────────────────────────────────

def _sort_key(event: dict) -> tuple:
    score = event.get("_score", 0)
    pages = len(event.get("pages", []))
    return (score, pages)


# ── Keyword fallback (used when Gemini is unavailable) ─────────────────────────

TIER_1_KEYWORDS = [
    "space", "moon landing", "orbit", "spacecraft", "astronaut", "cosmonaut",
    "apollo", "sputnik", "nasa", "satellite", "rocket",
    "discovery of", "invented", "invention", "patent", "breakthrough",
    "nuclear", "atomic", "penicillin", "vaccine", "dna", "genome", "x-ray",
    "telephone", "telegraph", "radio", "television", "internet", "computer",
    "aircraft", "airplane", "locomotive", "printing press",
    "assassination", "assassinated", "revolution", "independence declared",
    "treaty of", "surrender", "armistice", "abdicated",
    "world war", "d-day", "declared war", "invasion of", "fall of",
    "liberation of", "siege of", "battle of",
    "first broadcast", "first ever", "world premiere", "first transmission",
    "first flight", "first voyage",
]

TIER_2_KEYWORDS = [
    "coronation", "crowned", "elected president", "elected prime minister",
    "inaugurated",
    "earthquake", "tsunami", "hurricane", "eruption", "sank", "crashed",
    "explosion", "disappeared", "missing",
    "founded", "launched", "released", "published", "established",
]


def _keyword_fallback_score(event: dict) -> int:
    text = event.get("text", "")
    text_lower = text.lower()
    is_birth_death = any(pattern in text_lower for pattern in BIRTH_DEATH_PATTERNS)
    if is_birth_death and any(icon in text for icon in GLOBAL_ICONS):
        return 9
    if any(kw in text_lower for kw in TIER_1_KEYWORDS):
        return 6
    if any(kw in text_lower for kw in TIER_2_KEYWORDS):
        return 3
    return 1


# ── Public API ─────────────────────────────────────────────────────────────────

def select_event(
    events: list[dict], scoring_api_key: str | None = None
) -> tuple[dict, list[dict]]:
    """Score and rank events; return (best, top_4_runners_up)."""
    if not events:
        raise ValueError("No events to select from")

    eligible = [e for e in events if not _is_excluded(e)]
    if not eligible:
        eligible = events

    # Deduplicate before scoring — keyword overlap first (free), then semantic (Gemini)
    eligible = _deduplicate_overlap(eligible)
    logger.info("After keyword dedup: %d events", len(eligible))

    if scoring_api_key:
        try:
            eligible = _deduplicate_semantic(eligible, scoring_api_key)
        except Exception as exc:
            logger.warning("Semantic dedup failed, continuing with keyword-only dedup: %s", exc)

    # Categorise and score with Gemini Flash, falling back to keywords
    if scoring_api_key:
        try:
            categories_list = _categorise_with_gemini(eligible, scoring_api_key)
            for event, categories in zip(eligible, categories_list):
                event["_categories"] = categories
                event["_score"] = _calculate_score(categories, event.get("text", ""))
            logger.info("Categorised %d events with Gemini Flash", len(eligible))
        except Exception as exc:
            logger.warning("Gemini categorisation failed, falling back to keywords: %s", exc)
            for event in eligible:
                event["_score"] = _keyword_fallback_score(event)
    else:
        logger.warning("No scoring API key provided, using keyword fallback")
        for event in eligible:
            event["_score"] = _keyword_fallback_score(event)

    ranked = sorted(eligible, key=_sort_key, reverse=True)
    ranked = _deduplicate_topics(ranked)

    best = ranked[0]
    runners_up = ranked[1:5]
    return best, runners_up
