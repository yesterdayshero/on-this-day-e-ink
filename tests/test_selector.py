import pytest


def _event(text, year="1900", pages=None):
    return {"text": text, "year": year, "pages": pages or []}


def test_excludes_atrocity_events():
    from on_this_day.selector import select_event
    events = [
        _event("A genocide occurred in region X"),
        _event("Apollo 11 landed on the Moon", pages=[{}, {}]),
    ]
    best, runners = select_event(events)
    assert "Apollo" in best["text"]


def test_excludes_routine_birth():
    from on_this_day.selector import select_event
    events = [
        _event("John Smith was born in 1823"),
        _event("The telephone was invented by Alexander Graham Bell", pages=[{}, {}, {}]),
    ]
    best, runners = select_event(events)
    assert "telephone" in best["text"].lower()


def test_does_not_exclude_iconic_birth():
    from on_this_day.selector import select_event
    events = [
        _event("Albert Einstein was born in Ulm, Germany", pages=[{}, {}]),
        _event("A minor local road was opened", pages=[{}]),
    ]
    best, _ = select_event(events)
    assert "Einstein" in best["text"]


def test_tier1_beats_tier2():
    from on_this_day.selector import select_event
    events = [
        _event("The coronation of King George VI took place", pages=[{}]),  # Tier 2
        _event("The first television broadcast was made by the BBC", pages=[{}]),  # Tier 1
    ]
    best, _ = select_event(events)
    assert "television" in best["text"].lower()


def test_tier2_beats_tier3():
    from on_this_day.selector import select_event
    events = [
        _event("A new bridge was opened in the city", pages=[{}]),  # Tier 3
        _event("A major earthquake struck the region", pages=[{}]),  # Tier 2
    ]
    best, _ = select_event(events)
    assert "earthquake" in best["text"].lower()


def test_page_count_breaks_tie():
    from on_this_day.selector import select_event
    events = [
        _event("The telephone was invented", pages=[{}]),          # Tier 1, 1 page
        _event("The first orbit was achieved by Sputnik", pages=[{}, {}, {}]),  # Tier 1, 3 pages
    ]
    best, _ = select_event(events)
    assert "Sputnik" in best["text"]


def test_australian_boost_breaks_tier3_tie():
    from on_this_day.selector import select_event
    events = [
        _event("A new museum was opened in Sydney", pages=[{}]),   # Tier 3 + AU boost
        _event("A new museum was opened in London", pages=[{}]),   # Tier 3, no boost
    ]
    best, _ = select_event(events)
    assert "Sydney" in best["text"]


def test_returns_up_to_4_runners_up():
    from on_this_day.selector import select_event
    events = [_event(f"Event number {i}", pages=[{}] * i) for i in range(1, 8)]
    best, runners = select_event(events)
    assert len(runners) <= 4


def test_single_event_returns_empty_runners():
    from on_this_day.selector import select_event
    events = [_event("Only event", pages=[{}])]
    best, runners = select_event(events)
    assert runners == []


def test_raises_on_empty_events():
    from on_this_day.selector import select_event
    with pytest.raises(ValueError):
        select_event([])
