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

## 1. ✅ DONE: Polish the web app
- Calm premium-fintech design (Fraunces headlines, Manrope text, charcoal hero gradient with floating glass signature).
- Added progress loading line respecting `prefers-reduced-motion`.
- Grouped fixes table: "Fixed and proven" first, then "Needs a person", with count badges in headers.
- Enhanced screen-reader before/after comparison with changed lines highlighted via `<mark>`.
- Added "How it works" 3-step pipeline strip (Audit → Fix → Re-check) directly under the address form.
- Added one-click script tag copy with accessible clipboard status feedback.
- Styled severity tags (critical, serious, moderate, minor), code target chips, and interactive table row hover states.
- Added clean print media stylesheet for physical report prints and browser PDF export.
- Fully responsive across desktop (1280px), tablet (768px), and mobile (375px) with zero horizontal overflow.

## 2. ✅ DONE: Our own page must pass our own check
- Verified with `python a11y.py http://localhost:8765/ --no-ai --max-after 0`.
- Scored **0 problems** consistently across landing and results views; integrated into GitHub Actions CI.

## 3. ✅ DONE: Screenshots for Devpost
- Clean screenshots taken at 1440px wide and saved in `docs/screenshots/`:
  - `01-paste-a-url.png` (hero and paste box)
  - `02-result.png` (proven score card and ship panel)
  - `03-fixed-and-proven.png` (proven fixes table with WCAG tags)
  - `04-needs-a-person.png` (unfixed issues requiring human review)
  - `05-screen-reader-before-after.png` (screen-reader speech before/after)
  - `06-see-the-difference.png` (visual difference snapshots)
  - `07-ship-the-fixes.png` (fix script and single-line deployment)
  - `08-real-site-hacker-news.png` (real site check proof)

## 4. ✅ DONE: Help Ayush with the video
- Reviewed video script in `docs/DEVPOST.md` (Video plan) and coordinated screen recordings.

## 5. ✅ DONE: Your line for "What we learned"
- Added under "What we learned" in `docs/DEVPOST.md`:
  *"Our own page had to pass first. Building to zero problems on our own check, in CI, kept us honest about what we asked other sites to do."*
