# Ayush: demo video, demo page, more real pages

Deadline for the team: **11 Nov, 3:30 AM IST**. Code freeze **10 Nov, 9:00 PM IST**.
Branch: `ayush/<task>` → pull request into `main`. Run `python -m pytest -q` before every push.

## 1. More real pages in the benchmark (by 10 Nov, 12:00 PM)
- Files: `bench.py` (the `PAGES` list), `results/`
- Add 5-10 more public pages people really use: Indian government and university sites, a news site,
  a shopping site. Avoid pages that need a login.
- Run: `python bench.py` → `results/bench.csv`. Don't edit the CSV by hand.
- Done when: the CSV has the new pages, and any page that errors is left in with its error (honest).

## 2. Record the demo video (by 10 Nov, 8:00 PM)
- Follow the "Video plan" in `docs/DEVPOST.md`: under 3 minutes, never sped up.
- Show: the problem in one sentence → paste the demo page → numbers → table → screen-reader before/after →
  one real page (Hacker News 247 → 6) → how it works → repo link.
- Use only numbers that are in `results/` at the time you record. If Abhijeet's AI run is ready, show it too.
- Upload to YouTube as **public** or unlisted (check the Devpost rules allow unlisted), no copyrighted music.
- Done when: the YouTube link is in `docs/DEVPOST.md` under "Try it out" and you've sent it to Chirag.

## 3. Check the demo page still fails the way we planned
- Files: `demo/broken.html`. If anyone changes it, `test_a11y.py` must still pass.

## 4. Your line for "What we learned"
- Add it under "What we learned" in `docs/DEVPOST.md`.
