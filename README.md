# Ctrl+A11y

**Demo video (2 min):** https://youtu.be/WMV3hIreQyw

[![tests](https://github.com/thegoodengineers/ctrl-a11y/actions/workflows/test.yml/badge.svg)](https://github.com/thegoodengineers/ctrl-a11y/actions/workflows/test.yml)

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
- **Demo pages:** "Try our deliberately broken demo page" in the app: 10 problems found, **all 10 fixed and
  proven**, 0 new, with no AI model: the two images are described from the text inside them. A second test page (`demo/more.html`) covers spacer images, icon buttons, icon links, tab order,
  landmarks, dropdowns, linked images and layout slices: 12 of 12 fixed and proven. Both are checked by `test_a11y.py` on every run.
- **Real pages** (`results/bench.csv`, AI descriptions off, latest run 9 Nov 2026):

  | Page | Problems before | After | Fixes proven | Also resolved | Did not hold | Rolled back | New problems |
  |---|---|---|---|---|---|---|---|
  | W3C inaccessible demo, home | 67 | 28 | 33 | 6 | 0 | 0 | 0 |
  | W3C inaccessible demo, news | 52 | 25 | 27 | 0 | 0 | 0 | 0 |
  | python.org | 112 | 2 | 77 | 33 | 0 | 0 | 0 |
  | news.ycombinator.com | 246 | 1 | 245 | 0 | 0 | 0 | 0 |
  | craigslist.org/about/sites | 47 | 28 | 19 | 0 | 0 | 0 | 0 |
  | example.com | 9 | 9 | 0 | 0 | 0 | 0 | 0 |
  | **Total, 6 pages** | **533** | **93** | **401** | **39** | **0** | **0** | **0** |
  | india.gov.in, cbse.gov.in | site served a block or error page to the browser (HTTP 403); not scored | | | | | | |

  Honest reading: Hacker News is mostly low-contrast text. "After" can drop by more than the proven
  count, because one fix (like marking the main area) can clear several problems. example.com's text sits
  directly in the page body, so adding a main area needs a person.

## How it works
1. **Check:** opens the page in a real browser (Playwright + Chromium) and runs axe-core 4.10.2.
2. **Fix:** deterministic fixers, each saying where its fix came from (for example "Name added: Search, from
   its icon class"). Image descriptions and names with no honest clue on the page come from a vision AI model
   looking at the element (optional, needs a key); without it they go to a person.
3. **Re-check:** runs axe-core again. A fix counts only if the same rule no longer flags the same element.
   Problems that disappear because of a related fix (removing a broken `role="tree"` also repairs its list
   items) are reported as "also resolved", proven by the same re-check.
4. **Safety net:** if the re-check finds any new problem, the engine rebuilds the page from the original with
   fewer fixes (one kind at a time, then all structural changes, then none) until no new problem remains,
   and marks what it undid as "rolled back". A fix is never left in place if it made the page worse
   (`test_a_fix_that_creates_a_new_problem_is_rolled_back`). Pages that change on every load (carousels,
   tickers, random ids) are compared against a fresh unfixed copy, so the page's own changes are never
   blamed on a fix. Strict Content-Security-Policy sites are checked too.
5. **Ship:** a one-line fix script with only the proven fixes. Proven: on a fresh, untouched copy of the page,
   the script alone reproduces the engine's result (tests for both demo pages).
6. **Show:** every fix in plain language with its WCAG success criterion and severity, what a screen reader
   hears before and after, the fixed page, and a dated accessibility report (itself 0 problems on our check).
7. **Ctrl+V anywhere:** copy an address, press Ctrl+V anywhere on the page, and the check starts.
8. **See it and scale it:** before/after screenshots of the page, and one click to check up to 5 more pages on
   the same site. Hacker News, 6 pages (`results/site_news_ycombinator_com.csv`): 1,361 problems to 6,
   1,355 fixes proven, 0 failed, 0 new. Re-run with `python bench.py --site https://news.ycombinator.com/`.

## For people who use screen readers: fix pages as you browse
A "Fix this page" bookmarklet: add one bookmark, open it on any hard-to-use page, and that page gets our proven
fixes immediately; the screen reader announces "Ctrl+A11y applied 8 proven accessibility fixes to this page".
Checked end to end on the demo page: 10 problems down to 2. Keyboard and screen-reader users can copy the
bookmark code instead of dragging. Sites with a strict content security policy block outside scripts; then the
page simply stays as it was.

## For developers: block regressions in CI
```
python a11y.py https://your-site.example --no-ai --max-after 0 --script ctrl-a11y-fixes.js
```
Exits with code 1 when more problems remain than you allow, and writes the proven-fix script. Example GitHub
Actions step:
```yaml
- run: python -m pip install -r requirements.txt && python -m playwright install --with-deps chromium && npm ci
- run: python a11y.py https://staging.your-site.example --no-ai --max-after 0
```

## Not an overlay
Accessibility overlay widgets are widely criticised by blind users
([Overlay Fact Sheet](https://overlayfactsheet.com/en/)): they add their own toolbars, fight with screen
readers and guess. Ctrl+A11y is built the other way round:
- No widget, no toolbar, no tracking: the script only sets the same attributes a developer would.
- Only proven fixes ship; anything that made the page worse is rolled back automatically.
- Every fix is listed with the element and the exact change, so developers can copy it into their own source.
- Pages that block automated browsers are reported, not scored.
- The server only checks public addresses: private and internal network addresses are refused.

## Demo video, generated by code
`video/script.md` is the script; `narrate.py` makes the voice, `record.py` films every scene from the real app,
`assemble.py` joins them into `video/build/final.mp4` (116 seconds, never sped up). Edit a line and rebuild.

## Run it
```
python -m pip install -r requirements.txt
python -m playwright install chromium
npm install
python -m uvicorn server:app --port 8765     # open http://localhost:8765
python -m pytest -q                          # 7 checks: three demo pages, fix script, safety net, server safety
python bench.py                              # re-measure real pages -> results/bench.csv
python bench.py --out bench_india.csv URL... # any other set of pages -> results/bench_india.csv
python proof.py                              # fix script alone on fresh pages -> results/fix_script_proof.csv
python a11y.py https://example.com --no-ai   # command line
```
Optional AI descriptions: set `CTRL_A11Y_VISION_API_KEY` (an app-specific name, so the app never
picks up a key by accident), and `CTRL_A11Y_MODEL` to the vision model ID. Both stay in your own environment.

## Put it online (free)
One container holds the app and a real Chromium (`Dockerfile`; CI builds it and checks it fixes the demo page).

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/thegoodengineers/ctrl-a11y)

Click the button, sign in with GitHub, and Render builds it from `render.yaml` on its free plan. The server
allows one check at a time there (`CTRL_A11Y_MAX_RUNS`); extra visitors are asked to retry instead of crashing
it. Private and local addresses are refused, so the public demo can't be used to probe the network it runs on.
Any other Docker host works too (`deploy_hf.py` publishes to Hugging Face Spaces on a paid plan).

## Known limits
- The fix script repairs pages in the browser; editing the site's own source code (a pull request) is the next step.
- One page at a time; no logins, no PDFs.
- Heading order, missing headings and content outside every landmark that isn't clearly named are listed for a person.
- Text inside moving slideshows is listed for a person: its colours change mid-fade, so a fix can't be proven.
- Some sites block automated browsers; we report that instead of scoring the block page.
- Indian sites (`results/bench_india.csv`): 7 scored, 563 problems to 315, 244 fixes proven, 11 more resolved, 0 new problems.
  myScheme went from 29 to 0, The Hindu from 123 to 28, MyGov from 197 to 124.
  uidai.gov.in (HTTP 500) and ndtv.com (HTTP 403) block automated browsers.
