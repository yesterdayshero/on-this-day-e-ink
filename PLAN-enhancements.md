# On This Day E-Ink — Enhancements

Post-launch improvements and ideas. Not blocking core functionality.

- [ ] **Port cultural scoring improvements from TRMNL** — `cultural_milestone` scoring updated to 3 pts (was 2). New `iconic_entertainment` category (4 pts) for globally iconic premieres, landmark franchise debuts, and major cultural firsts that defined a generation (e.g. Star Wars premiere, The Simpsons debut, The Beatles' US TV debut). Update `CATEGORY_POINTS` in `selector.py` and the categorisation prompt to match current TRMNL implementation.
- [ ] **Port visual scene extraction from TRMNL** — Add `describer.py` module that makes a single Gemini text call on the winning event, returning both a display caption and a concrete visual scene description. Replaces passing raw Wikipedia text to the image generator, fixing meta-imagery (press conferences, announcement screens) caused by Wikipedia's announcement-framed event descriptions. See TRMNL `src/on_this_day/describer.py` for the implementation to port.
