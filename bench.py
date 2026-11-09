"""Run the engine on real pages and write every number to results/bench.csv. Only these numbers go in the pitch."""
import csv
import datetime
import pathlib
import subprocess
import sys

import a11y

PAGES = [
    "https://www.w3.org/WAI/demos/bad/before/home.html",  # W3C's official deliberately inaccessible demo
    "https://www.w3.org/WAI/demos/bad/before/news.html",
    "https://www.india.gov.in/",
    "https://www.cbse.gov.in/",
    "https://www.python.org/",
    "https://news.ycombinator.com/",
    "https://www.craigslist.org/about/sites",
    "https://example.com/",
]

if __name__ == "__main__":
    pages = sys.argv[1:] or PAGES
    out = pathlib.Path(__file__).parent / "results" / "bench.csv"
    out.parent.mkdir(exist_ok=True)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or "uncommitted"
    when = datetime.datetime.now().isoformat(timespec="seconds")
    rows = []
    for url in pages:
        try:
            r = a11y.run(url, describe=False)
            row = {"url": url, "before": r["before"], "after": r["after"], "verified": r["verified"],
                   "failed_recheck": sum(f["status"] == "failed re-check" for f in r["fixes"]),
                   "new_problems": len(r["new_problems"]), "error": ""}
        except Exception as e:
            row = {"url": url, "before": "", "after": "", "verified": "", "failed_recheck": "", "new_problems": "",
                   "error": str(e).splitlines()[0][:120]}
        row.update(ai="off", commit=commit, run_at=when)
        rows.append(row)
        print(row)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    ok = [r for r in rows if not r["error"]]
    print(f"\n{len(ok)}/{len(rows)} pages audited · problems {sum(r['before'] for r in ok)} -> {sum(r['after'] for r in ok)}"
          f" · fixes proven {sum(r['verified'] for r in ok)} · failed re-check {sum(r['failed_recheck'] for r in ok)}"
          f" · new problems {sum(r['new_problems'] for r in ok)}")
