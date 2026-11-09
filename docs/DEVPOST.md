# Devpost submission text (draft)

Every number below comes from `results/bench.csv` or `test_a11y.py`. If you re-run the benchmark,
update the numbers here. Replace anything in [brackets] before submitting.

## Project overview
**Project name** (60 max): `Ctrl+A11y: paste a URL, get an accessible site` (46)

**Elevator pitch** (200 max, 180 used):
`Paste any URL. An AI agent finds the accessibility barriers, fixes them, and proves every fix by re-running the same checker, so blind and keyboard users can actually use the page.`

## Project details: About the project

### Inspiration
Many websites still have barriers that stop people from using them: images with no description,
form fields with no label, text too faint to read, buttons a screen reader announces only as "button".
Checkers that list these problems already exist. What's missing is getting them fixed, and knowing a
fix actually worked. We wanted the Ctrl+V of accessibility: paste a page, get it back usable.

### What it does
1. You paste a web page's address.
2. Ctrl+A11y opens it in a real browser and runs axe-core, the standard accessibility checker.
3. It fixes what it can: missing form labels, page language, page title, frame titles and low-contrast
   text. With AI turned on, it also writes image descriptions and names for icon-only buttons and links,
   by looking at the element itself.
4. It runs the same checker again. A fix counts only if the same rule no longer flags the same element.
   If anything new breaks, it undoes the fix that caused it automatically.
5. You get a one-line fix script with only the proven fixes. Add one script tag to your page and the fixes go
   live today. We proved it: on a fresh copy of Hacker News, the script alone takes it from 247 problems to 6,
   exactly what the engine measured.
6. You see every problem with what was done or why it needs a person, and what a screen reader hears before
   and after.
7. People who use screen readers can add a "Fix this page" bookmark. On any hard-to-use page, it applies the
   proven fixes immediately and announces how many it applied. On our demo page: 10 problems down to 2.
8. Developers can run it in CI: it fails the build when more problems remain than they allow.
9. Every problem shows its WCAG success criterion and severity, and you can download a dated, printable
   accessibility report. Copy an address and press Ctrl+V anywhere on our page to start, true to the name.
10. Before/after screenshots, and one click to check up to 5 more pages of the same site. On 6 Hacker News
   pages: 1,364 problems down to 12, with 1,352 fixes proven and 0 new problems.

### How we built it
Python, Playwright and Chromium for a real browser; axe-core 4.10.2 for checking; FastAPI for the app;
plain HTML and JavaScript for the interface; a vision AI model for image and icon
descriptions. The fixers are plain code, so the same input always gives the same fix. A test checks the
demo page result on every run, and a benchmark script measures real pages into a CSV.

### Results
Why it matters: the WebAIM Million 2026 found 56.1 accessibility errors per home page on average across the
top million sites, and its six most common failures (low contrast 83.9%, missing image descriptions 53.1%,
missing form labels 51%, empty links 46.3%, empty buttons 30.6%, missing page language 13.5%) are exactly
the six we fix.

On our two planted demo pages: 10 problems with 8 fixed and proven, and 9 of 9 fixed and proven, with
0 new problems. The rest need image descriptions from the vision model.

On 6 real public pages with AI off: 526 problems before, 93 after, 389 fixes proven, 0 that failed the
re-check, 0 rolled back, 0 new problems. Python.org went from 120 to 2; Hacker News from 247 to 2.
Two government sites served an "Access Denied" page to automated browsers, so we report them as not
scored instead of measuring the block page. Our own page scores 0 problems on our own check.

### Challenges we ran into
- A fix can make a page worse: our first landmark fixer marked a heading as the main area on a block page.
  We added a safety net that undoes any fix that creates a new problem, and tested it by sabotaging a fixer on purpose.
- Some sites block automated browsers; we detect that and report it instead of scoring the block page.
- Making "fixed" mean something: we re-run the checker and match each fix to the exact element, instead
  of trusting our own fix.
- Colours arrive in different formats from the checker; one fixer crashed the whole run until we isolated
  each fix so one failure can't stop the others.
- Not guessing: when there is no honest clue for a name or description, we report it for a person.
- Keeping our own keys safe: the app only uses a key set for it by name, never one it finds lying around.

### Accomplishments that we're proud of
- Not an overlay: no widget, no tracking, only proven attribute fixes that developers can copy into their own source.
- Zero new problems introduced across every page we tested.
- Every claim on screen is backed by the re-check, and failures are shown as failures.
- The interface follows the same rules it checks for: labelled input, keyboard focus, live status messages.

### What we learned
[Each of us: one line.]

### What's next
- Turn verified fixes into a pull request on the site's own source code, as well as the fix script.
- Whole-site crawls, PDFs, and the rules that need judgement (heading order, landmarks).
- Descriptions in the user's language.

## Built with
`python` `playwright` `chromium` `axe-core` `fastapi` `javascript` `html` `css` `anthropic`

## Try it out
- Repo: https://github.com/thegoodengineers/ctrl-a11y
- Demo video: [YouTube link, under 3 minutes]

## Video plan (under 3 minutes)
1. 0:00 Problem in one sentence; a screen reader reading the broken demo ("button, link, image").
2. 0:20 Paste the demo URL, click Fix: 10 found, 7 proven, 0 new.
3. 0:50 Scroll the list: proven fixes and "needs a person" with reasons.
4. 1:20 Screen-reader view, before vs after.
5. 1:50 One real page (Hacker News: 247 to 6).
6. 2:20 How it works in one diagram; the re-check is the point.
7. 2:45 Close: repo link.
