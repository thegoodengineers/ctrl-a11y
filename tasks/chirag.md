# Chirag: lead, engine, final submission

Deadline for the team: **11 Nov, 3:30 AM IST**. Code freeze **10 Nov, 9:00 PM IST**. Submit by **10 Nov, 11:00 PM IST**.
Branch: `chirag/<task>` → pull request into `main`. Run `python -m pytest -q` before every push.

## 1. Fix the 3 contrast fixes that fail the re-check (by 10 Nov, 12:00 PM)
- Files: `a11y.py` (`FIX_JS`, the `color-contrast` branch)
- Reproduce: `python a11y.py https://www.python.org/ --no-ai` and look for `failed re-check`.
- Likely causes to check: text over a background image or gradient, a parent with opacity, or a pseudo-element.
  If it can't be fixed honestly, change the fixer to skip it with a clear reason instead of applying a fix that fails.
- Done when: re-running shows 0 `failed re-check` on python.org (fixed or honestly skipped), and the test passes.

## 2. Review and merge everyone's pull requests (ongoing, until 9:00 PM on 10 Nov)
- Check each PR runs `python -m pytest -q` green and doesn't put any number in docs that isn't in `results/`.

## 3. Final benchmark and numbers (10 Nov, 9:00 PM, after code freeze)
- Run `python bench.py` (and the AI-on run from Abhijeet's file if his key works).
- Update the results table in `README.md` and the numbers in `docs/DEVPOST.md` from `results/bench.csv`.

## 4. Submit on Devpost (10 Nov, 11:00 PM)
- Paste from `docs/DEVPOST.md`: name, pitch, About the project, Built with, repo link, video link (from Ayush).
- Add screenshots (from Bhumika). Check every link in an incognito window.
- Done when: Devpost shows the project as submitted, not draft.

## 5. Your line for "What we learned"
- Add it under "What we learned" in `docs/DEVPOST.md`.
