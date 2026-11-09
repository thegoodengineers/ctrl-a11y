# Ctrl+A11y

**Paste a URL, get an accessible site.** An agent finds what blocks blind, low-vision and keyboard
users, fixes what it can, and proves every fix by running the same accessibility check again.

Built for the [Ctrl+V Hackathon](https://ctrl-v-hackathon-31831.devpost.com/) (6-10 Nov 2026) by
Chirag, Bhumika, Ayush and Abhijeet (The Good Engineers).

## For judges, start here
- **Our own page:** 0 problems on our own check (`python a11y.py http://localhost:8765/ --no-ai`).
- **Demo page:** run the app and click "Try our deliberately broken demo page": 10 problems found,
  7 fixed and proven, 0 new problems (`test_a11y.py` checks this on every run).
- **Real pages** (`results/bench.csv`, 8 public pages, AI descriptions off, latest run 9 Nov 2026):

  | Page | Problems before | After | Fixes proven | Fix did not hold | New problems |
  |---|---|---|---|---|---|
  | W3C inaccessible demo, home | 67 | 64 | 3 | 0 | 0 |
  | W3C inaccessible demo, news | 52 | 51 | 1 | 0 | 0 |
  | india.gov.in | 5 | 4 | 1 | 0 | 0 |
  | cbse.gov.in | 5 | 4 | 1 | 0 | 0 |
  | python.org | 120 | 98 | 17 | 0 | 0 |
  | news.ycombinator.com | 247 | 6 | 241 | 0 | 0 |
  | craigslist.org/about/sites | 31 | 28 | 3 | 0 | 0 |
  | example.com | 9 | 9 | 0 | 0 | 0 |
  | **Total** | **536** | **264** | **267** | **0** | **0** |

  Honest reading: most of the gain is low-contrast text (241 of the 267 on Hacker News). "After" can drop by
  more than the proven count, because one fix sometimes clears a related problem. Without the
  AI step, images and icon-only buttons are reported as "needs a person", not guessed.

## How it works
1. **Audit:** opens the page in a real browser (Playwright + Chromium) and runs axe-core.
2. **Fix:** deterministic fixers for missing labels, page language, page title, frame titles and colour
   contrast. Image descriptions and names for icon-only buttons and links come from a vision AI model, looking at
   a screenshot of the element (optional, needs a key).
3. **Prove it:** runs axe-core again on the fixed page. A fix counts only if the same rule no longer
   flags the same element. Any new problem is reported.
4. **Ship it:** a one-line fix script with only the proven fixes. Add `<script src="ctrl-a11y-fixes.js"></script>` to
   the page and the fixes go live. Proven: on a fresh, untouched copy, the script alone reproduces the engine's result
   (Hacker News 247 → 6, python.org 120 → 98; demo page checked by `test_fix_script_on_original_page_gives_same_result`).
5. **Show it:** what a screen reader hears, before and after, and a download of the fixed page.

## Run it
```
pip install -r requirements.txt
python -m playwright install chromium
npm install
python -m uvicorn server:app --port 8765     # open http://localhost:8765
python -m pytest -q                          # the demo-page check
python bench.py                              # re-measure real pages -> results/bench.csv
python a11y.py https://example.com --no-ai   # command line
```
Optional AI descriptions: set `CTRL_A11Y_ANTHROPIC_API_KEY` (an app-specific name, so the app never
picks up a key by accident), and `CTRL_A11Y_MODEL` to the vision model ID. Both stay in your own environment.

## Known limits
- The fix script repairs pages in the browser; editing the site's own source code (a pull request) is the next step.
- One page at a time; no logins, no PDFs.
- Rules it does not fix (headings order, landmarks, ARIA misuse and more) are listed for a person.
- Text inside moving slideshows is listed for a person: its colours change mid-fade, so a fix can't be proven.
