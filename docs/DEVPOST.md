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
4. It runs the same checker again. A fix counts only if the same rule no longer flags the same element,
   and any new problem would be reported.
5. You see every problem with what was done or why it needs a person, what a screen reader hears before
   and after, and you can download the fixed page.

### How we built it
Python, Playwright and Chromium for a real browser; axe-core 4.10.2 for checking; FastAPI for the app;
plain HTML and JavaScript for the interface; a vision AI model for image and icon
descriptions. The fixers are plain code, so the same input always gives the same fix. A test checks the
demo page result on every run, and a benchmark script measures real pages into a CSV.

### Results
On our deliberately broken demo page: 10 problems, 7 fixed and proven, 0 new problems. The 3 left
are images and an icon link, which need the AI step.

On 8 real public pages with AI off: 536 problems before, 266 after, 270 fixes proven, 3 fixes that did
not hold (shown as failures, not hidden), 0 new problems. Most of the gain was low-contrast text
(241 fixes on Hacker News). On the W3C's own inaccessible demo pages the gain is small (67 to 64,
52 to 51), because most of their problems need a person or the AI step. [Add the AI-on numbers if we run them.]

### Challenges we ran into
- Making "fixed" mean something: we re-run the checker and match each fix to the exact element, instead
  of trusting our own fix.
- Colours arrive in different formats from the checker; one fixer crashed the whole run until we isolated
  each fix so one failure can't stop the others.
- Not guessing: when there is no honest clue for a name or description, we report it for a person.
- Keeping our own keys safe: the app only uses a key set for it by name, never one it finds lying around.

### Accomplishments that we're proud of
- Zero new problems introduced across every page we tested.
- Every claim on screen is backed by the re-check, and failures are shown as failures.
- The interface follows the same rules it checks for: labelled input, keyboard focus, live status messages.

### What we learned
[Each of us: one line.]

### What's next
- Turn verified fixes into a pull request on the site's own code, not just a patched copy.
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
