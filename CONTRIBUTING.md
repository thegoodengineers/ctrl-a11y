# Working on Ctrl+A11y

Deadline: **11 Nov 2026, 3:30 AM IST** (Devpost). Aim to be done by 10 Nov, 11 PM IST.

## Setup (once)
```
git clone https://github.com/thegoodengineers/ctrl-a11y.git
cd ctrl-a11y
python -m pip install -r requirements.txt
python -m playwright install chromium
npm install
python -m pytest -q        # must pass before you start
```

## How we work
- Branch per task: `git checkout -b yourname/short-task`. Open a pull request into `main`.
- Run `python -m pytest -q` before every push. Don't merge a red test.
- Every number we show judges comes from `results/bench.csv` (re-run `python bench.py`). No made-up numbers.
- Never commit API keys. Keys go in your own environment (`CTRL_A11Y_VISION_API_KEY`).
- The engine reports what it can't fix as "needs a person". Keep it that way: never guess a fix.
- **Never name any AI assistant or chatbot used to build this**: not in commits, co-author lines, comments, docs,
  Devpost text, screenshots or the video. `git log --format=%B | grep -i co-authored` must print nothing.

## Who owns what (swap freely, keep one owner per part)
| Part | Files | Owner |
|---|---|---|
| Engine and fixers | `a11y.py` | Chirag |
| Web app and design | `web/index.html`, `server.py` | Bhumika |
| Demo page and benchmark | `demo/`, `bench.py`, `results/` | Ayush |
| AI descriptions and new fixers | `a11y.py` (`_describe`, `FIX_JS`) | Abhijeet |
| Video, screenshots, Devpost text | `docs/` | Bhumika + Ayush |

## Your tasks: one file each
| Who | File | Main job |
|---|---|---|
| Chirag | [`tasks/chirag.md`](tasks/chirag.md) | Fix failed re-checks, review PRs, final numbers, submit |
| Abhijeet | [`tasks/abhijeet.md`](tasks/abhijeet.md) | AI descriptions working and measured |
| Bhumika | [`tasks/bhumika.md`](tasks/bhumika.md) | Web app polish, our own page passes our check, screenshots |
| Ayush | [`tasks/ayush.md`](tasks/ayush.md) | More real pages, demo video |
Tick the boxes in your own file as you finish. Code freeze **10 Nov, 9:00 PM IST**; submit **10 Nov, 11:00 PM IST**.

## How we win (judging weights from the official rules)
| Criterion | Weight | What wins it | Who |
|---|---|---|---|
| Impact | 30% | AI descriptions working, so images and icon buttons get fixed too: that's what blind users hit most. Real Indian sites in the benchmark | Abhijeet, Ayush |
| Innovation | 25% | Say it clearly everywhere: other tools only report problems; we fix them and **prove** every fix with a re-check | Everyone, in the video and text |
| Technical | 25% | 0 failed re-checks, 0 new problems, tests green, honest numbers | Chirag, Abhijeet |
| User Experience | 10% | A clean app, and our own page scoring 0 problems on our own check | Bhumika |
| Presentation | 10% | A tight video under 3 minutes with the screen-reader before/after moment | Ayush, Bhumika |
Ties go to Impact, then Innovation, so those two come first.
