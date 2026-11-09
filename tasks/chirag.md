# Chirag: lead, engine, final submission

Deadline for the team: **11 Nov, 3:30 AM IST**. Code freeze **10 Nov, 9:00 PM IST**. Submit by **10 Nov, 11:00 PM IST**.

## Rule for everyone: never name the AI tools we used to build this
Do not name any AI assistant or chatbot used to build this project anywhere: commit messages, co-author lines,
code comments, README, docs, Devpost text, screenshots or the video. No `Co-Authored-By` lines for AI tools.
Describing the product's own feature ("a vision AI model writes image descriptions") is fine.
Before you push: `git log --format=%B | grep -i co-authored` must print nothing.
Branch: `chirag/<task>` → pull request into `main`. Run `python -m pytest -q` before every push.

## 1. ✅ DONE 9 Nov: fix the 3 contrast fixes that fail the re-check
- Cause: text in python.org's rotating slideshow, measured mid-fade; the slide changed before the re-check.
  Now skipped with the reason "inside a moving slideshow". python.org: 0 failed, 17 proven. Test: `test_slideshow_text_is_skipped_not_failed`.
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
