# Ctrl+A11y

**Paste a URL, get an accessible site.** An agent finds what blocks blind, low-vision and keyboard
users, fixes what it can, and proves every fix by running the same accessibility check again.

Built for the [Ctrl+V Hackathon](https://ctrl-v-hackathon-31831.devpost.com/) (6-10 Nov 2026) by
Chirag, Bhumika, Ayush and Abhijeet (The Good Engineers).

## Why it matters
The [WebAIM Million 2026](https://webaim.org/projects/million/) tested the home pages of the top
1,000,000 websites and found 56.1 errors per page on average. The six most common failures are exactly
the six we fix:

| Failure | Share of home pages | What we do |
|---|---|---|
| Low contrast text | 83.9% | Adjust the text colour until it passes |
| Missing image descriptions | 53.1% | Mark spacers decorative; take names from captions, link titles; vision model for the rest |
| Missing form labels | 51% | Label from placeholder, name, id or first option |
| Empty links | 46.3% | Name from icon title, icon class, image description or link address |
| Empty buttons | 30.6% | Same as links |
| Missing page language | 13.5% | Set it when the page is clearly English |

## For judges, start here
- **Our own page:** 0 problems on our own check, landing page and results view, at 1280 and 375 px wide.
- **Demo pages:** "Try our deliberately broken demo page" in the app: 10 problems found, 7 fixed and proven,
  0 new. A second test page (`demo/more.html`) covers spacer images, icon buttons, icon links, tab order,
  landmarks and dropdowns: 9 of 9 fixed and proven. Both are checked by `test_a11y.py` on every run.
- **Real pages** (`results/bench.csv`, AI descriptions off, latest run 9 Nov 2026):

  | Page | Problems before | After | Fixes proven | Did not hold | Rolled back | New problems |
  |---|---|---|---|---|---|---|
  | W3C inaccessible demo, home | 67 | 38 | 23 | 0 | 0 | 0 |
  | W3C inaccessible demo, news | 52 | 35 | 17 | 0 | 0 | 0 |
  | python.org | 120 | 2 | 80 | 0 | 0 | 0 |
  | news.ycombinator.com | 247 | 2 | 245 | 0 | 0 | 0 |
  | craigslist.org/about/sites | 31 | 7 | 24 | 0 | 0 | 0 |
  | example.com | 9 | 9 | 0 | 0 | 0 | 0 |
  | **Total, 6 pages** | **526** | **93** | **389** | **0** | **0** | **0** |
  | india.gov.in, cbse.gov.in | served "Access Denied" (HTTP 403) to the browser, so **not scored** | | | | | |

  Honest reading: Hacker News is mostly low-contrast text. "After" can drop by more than the proven
  count, because one fix (like marking the main area) can clear several problems. example.com's text sits
  directly in the page body, so adding a main area needs a person.

## How it works
1. **Check:** opens the page in a real browser (Playwright + Chromium) and runs axe-core 4.10.2.
2. **Fix:** deterministic fixers, each saying where its fix came from (for example "Name added: Search, from
   its icon class"). Image descriptions and names with no honest clue on the page come from a vision AI model
   looking at the element (optional, needs a key); without it they go to a person.
3. **Re-check:** runs axe-core again. A fix counts only if the same rule no longer flags the same element.
4. **Safety net:** if the re-check finds any new problem, the engine rebuilds the page from the original with
   fewer fixes (one kind at a time, then all structural changes, then none) until no new problem remains,
   and marks what it undid as "rolled back". A fix is never left in place if it made the page worse
   (`test_a_fix_that_creates_a_new_problem_is_rolled_back`).
5. **Ship:** a one-line fix script with only the proven fixes. Proven: on a fresh, untouched copy of the page,
   the script alone reproduces the engine's result (tests for both demo pages).
6. **Show:** every fix in plain language, what a screen reader hears before and after, and the fixed page.

## Not an overlay
Accessibility overlay widgets are widely criticised by blind users
([Overlay Fact Sheet](https://overlayfactsheet.com/en/)): they add their own toolbars, fight with screen
readers and guess. Ctrl+A11y is built the other way round:
- No widget, no toolbar, no tracking: the script only sets the same attributes a developer would.
- Only proven fixes ship; anything that made the page worse is rolled back automatically.
- Every fix is listed with the element and the exact change, so developers can copy it into their own source.
- Pages that block automated browsers are reported, not scored.

## Run it
```
pip install -r requirements.txt
python -m playwright install chromium
npm install
python -m uvicorn server:app --port 8765     # open http://localhost:8765
python -m pytest -q                          # 5 checks, including both demo pages and the safety net
python bench.py                              # re-measure real pages -> results/bench.csv
python a11y.py https://example.com --no-ai   # command line
```
Optional AI descriptions: set `CTRL_A11Y_ANTHROPIC_API_KEY` (an app-specific name, so the app never
picks up a key by accident), and `CTRL_A11Y_MODEL` to the vision model ID. Both stay in your own environment.

## Known limits
- The fix script repairs pages in the browser; editing the site's own source code (a pull request) is the next step.
- One page at a time; no logins, no PDFs.
- Heading order, missing headings and content outside every landmark that isn't clearly named are listed for a person.
- Text inside moving slideshows is listed for a person: its colours change mid-fade, so a fix can't be proven.
- Some sites block automated browsers; we report that instead of scoring the block page.
