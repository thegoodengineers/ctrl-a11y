# Bhumika: web app design, our own accessibility, screenshots

Deadline for the team: **11 Nov, 3:30 AM IST**. Code freeze **10 Nov, 9:00 PM IST**.

## Rule for everyone: never name the AI tools we used to build this
Do not name any AI assistant or chatbot used to build this project anywhere: commit messages, co-author lines,
code comments, README, docs, Devpost text, screenshots or the video. No `Co-Authored-By` lines for AI tools.
Describing the product's own feature ("a vision AI model writes image descriptions") is fine.
Before you push: `git log --format=%B | grep -i co-authored` must print nothing.
Branch: `bhumika/<task>` → pull request into `main`. Run `python -m pytest -q` before every push.

## What changed since this file was written (9 Nov evening)
- The page was restyled (calm premium look) and gained new panels: the screen-reader bookmark, see the difference
  (screenshots), check more of this site, the downloadable report, WCAG labels on every problem.
- CI now fails if our own page has any problem, so keep running `python a11y.py http://localhost:8765/ --no-ai`
  after every change. Review the new panels on a phone-width window, and take the Devpost screenshots of them.

## 1. Polish the web app (by 10 Nov, 3:00 PM)
- Status 9 Nov: the page now follows a calm premium-fintech look (team's choice): light serif headlines (Fraunces),
  Manrope text, a big charcoal gradient hero panel with floating glass tiles, a centred statement, rounded step cards,
  a big proven-fixes score card next to a charcoal "Ship the fixes" card. Checked at 1280, 768 and 375 px: landing and
  results view both score 0 problems. Your job now: review it, improve anything that feels off, keep all views at 0.
  The list below is what's still open.
- Files: `web/index.html` (and `server.py` only if you need a new endpoint)
- User Experience is 10% of the score. Ideas, in order of value:
  1. A loading state while it runs (a progress line or spinner that respects reduced motion).
  2. Group the table: "Fixed and proven" first, then "Needs a person", with counts in each heading.
  3. Make the before/after screen-reader view easier to compare (highlight lines that changed).
  4. A short "How it works" strip under the paste box: Audit → Fix → Re-check.
- Keep it plain and readable: high contrast, big text, works at phone width with no sideways scrolling.

## 2. Our own page must pass our own check (by 10 Nov, 3:00 PM)
- Start the server: `python -m uvicorn server:app --port 8765`
- Run: `python a11y.py http://localhost:8765/ --no-ai`
- Status 9 Nov: it already reports **0 problems**. Keep it at 0 after your design changes.
- Done when: it reports **0 problems** on our own page. Screenshot that result; it's a great line for the video.

## 3. Screenshots for Devpost (by 10 Nov, 8:00 PM)
- 4-5 clean screenshots at 1440 px wide: paste box, result numbers, the fixes table, screen-reader before/after,
  and our own page passing. Save them in `docs/screenshots/` and give them to Chirag.

## 4. Help Ayush with the video
- Review the video script in `docs/DEVPOST.md` (Video plan) and record the screen parts with Ayush.

## 5. Your line for "What we learned"
- Add it under "What we learned" in `docs/DEVPOST.md`.
