# Abhijeet: AI descriptions (images and icon-only buttons/links)

Deadline for the team: **11 Nov, 3:30 AM IST**. Code freeze **10 Nov, 9:00 PM IST**.

## Rule for everyone: never name the AI tools we used to build this
Do not name any AI assistant or chatbot used to build this project anywhere: commit messages, co-author lines,
code comments, README, docs, Devpost text, screenshots or the video. No `Co-Authored-By` lines for AI tools.
Describing the product's own feature ("a vision AI model writes image descriptions") is fine.
Before you push: `git log --format=%B | grep -i co-authored` must print nothing.
Branch: `abhijeet/<task>` → pull request into `main`. Run `python -m pytest -q` before every push.

## What changed since this file was written (9 Nov evening)
- Many images no longer need the AI step: spacers and layout slices are marked decorative, linked images take
  their link's purpose, and SVG images use the words inside them. The demo page is now 10 of 10 fixed with AI off.
- Where AI still matters: real photos and raster images with no clue on the page, e.g. the W3C demo home page
  (`https://www.w3.org/WAI/demos/bad/before/home.html`). Measure AI on vs off there; that is the clearest proof of its value.
- The AI step reads `CTRL_A11Y_ANTHROPIC_API_KEY` and `CTRL_A11Y_MODEL` from your own environment only.

## 1. Turn the AI step on and prove it works (by 10 Nov, 12:00 PM)
- Files: `a11y.py` (`_describe`, and the `image-alt` / `button-name` / `link-name` branch of `FIX_JS`)
- Get an Anthropic API key from https://console.anthropic.com and set it only in your own terminal:
  - PowerShell: `$env:CTRL_A11Y_ANTHROPIC_API_KEY = "your key"`
  - bash: `export CTRL_A11Y_ANTHROPIC_API_KEY="your key"`
  - Also set `CTRL_A11Y_MODEL` to the vision model ID from the provider's model list (Chirag has it).
  - Never commit either, never paste the key in chat or in a file in the repo.
- Run: `python a11y.py http://localhost:8765/demo/broken.html` (start the server first:
  `python -m uvicorn server:app --port 8765`).
- Done when: on the demo page the two images and the icon link show `verified`, so the demo goes from 10 to 0 or close,
  and the descriptions are correct for what the images show ("SkyTrips logo", "Goa from Rs 2,999 offer banner" or similar).

## 2. Benchmark with AI on (by 10 Nov, 6:00 PM)
- Make `bench.py` accept `--ai` and write `ai=on` rows to `results/bench_ai.csv` (keep `bench.csv` as the AI-off run).
- Run it on the same 8 pages. Note the cost in your PR (count of AI calls is enough).
- Done when: `results/bench_ai.csv` exists and Chirag can put both runs side by side in the README.

## 3. Check the AI never guesses (by 10 Nov, 6:00 PM)
- Spot-check 10 descriptions it wrote on real pages. If any is wrong or invented, tighten the prompt in `_describe`.
- Write what you found (how many were right) in your PR description. That number can go in the pitch.

## 4. Your line for "What we learned"
- Add it under "What we learned" in `docs/DEVPOST.md`.
