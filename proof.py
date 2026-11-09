"""Prove the shipped fix script works on its own: run the engine, then load a fresh, untouched copy of each page,
add only the fix script, and check again. Writes results/fix_script_proof.csv."""
import csv
import datetime
import pathlib
import subprocess
import sys

from playwright.sync_api import sync_playwright

import a11y

HERE = pathlib.Path(__file__).parent
PAGES = ["https://news.ycombinator.com/", "https://www.python.org/", (HERE / "demo/broken.html").resolve().as_uri()]

if __name__ == "__main__":
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    when = datetime.datetime.now().isoformat(timespec="seconds")
    rows = []
    for url in sys.argv[1:] or PAGES:
        r = a11y.run(url, describe=False)
        with sync_playwright() as p:
            page = p.chromium.launch().new_page(bypass_csp=True)
            a11y._open(page, url)
            fresh = len(a11y._audit(page))
            page.add_script_tag(content=r["fix_script"])  # the same script the download and the bookmark serve
            with_script = len(a11y._audit(page))
        row = {"url": url if url.startswith("http") else "demo/broken.html", "engine_before": r["before"],
               "engine_after": r["after"], "fresh_page_before": fresh, "fresh_page_with_script": with_script,
               "commit": commit, "run_at": when}
        print(row); rows.append(row)
    with (HERE / "results" / "fix_script_proof.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
