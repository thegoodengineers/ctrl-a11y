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

NAMES = {"https://www.w3.org/WAI/demos/bad/before/home.html": "W3C inaccessible demo, home",
         "https://www.w3.org/WAI/demos/bad/before/news.html": "W3C inaccessible demo, news"}


def readme_table():
    """Rewrite the results table in README.md from results/bench.csv, so the README can't drift from the data."""
    import re
    rows = list(csv.DictReader(open(pathlib.Path(__file__).parent / "results" / "bench.csv", encoding="utf-8")))
    ok = [r for r in rows if not r["error"]]
    name = lambda u: NAMES.get(u, u.split("//")[1].rstrip("/").replace("www.", ""))
    tot = lambda k: sum(int(r[k]) for r in ok)
    lines = ["  | Page | Problems before | After | Fixes proven | Also resolved | Did not hold | Rolled back | New problems |",
             "  |---|---|---|---|---|---|---|---|"]
    lines += [f"  | {name(r['url'])} | {r['before']} | {r['after']} | {r['verified']} | {r['resolved']} | {r['failed_recheck']} | {r['rolled_back']} | {r['new_problems']} |" for r in ok]
    lines.append(f"  | **Total, {len(ok)} pages** | **{tot('before')}** | **{tot('after')}** | **{tot('verified')}** | **{tot('resolved')}** | **{tot('failed_recheck')}** | **{tot('rolled_back')}** | **{tot('new_problems')}** |")
    bad = [r for r in rows if r["error"]]
    if bad:
        lines.append(f"  | {', '.join(name(r['url']) for r in bad)} | {bad[0]['error']} | | | | | | |")
    readme = pathlib.Path(__file__).parent / "README.md"
    text = readme.read_text(encoding="utf-8")
    nl = chr(10)
    text = re.sub(r"  \| Page \| Problems before \|.*?" + nl + "(?=" + nl + ")",
                  lambda m: nl.join(lines) + nl, text, count=1, flags=re.S)
    readme.write_text(text, encoding="utf-8")
    print(nl.join(lines))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--readme"]:
        readme_table(); sys.exit()
    out = pathlib.Path(__file__).parent / "results" / "bench.csv"
    if sys.argv[1:2] == ["--site"]:
        # Whole-site mode: the page plus up to 5 same-site pages it links to, as the app's site check does.
        first = a11y.run(sys.argv[2], describe=False)
        pages = [sys.argv[2]] + first["site_links"]
        out = out.with_name("site_" + sys.argv[2].split("//")[1].split("/")[0].replace(".", "_") + ".csv")
    elif sys.argv[1:2] == ["--out"]:  # extra page sets (e.g. Indian sites) without touching bench.csv
        out = out.with_name(sys.argv[2]); pages = sys.argv[3:]
    else:
        pages = sys.argv[1:] or PAGES
    out.parent.mkdir(exist_ok=True)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or "uncommitted"
    when = datetime.datetime.now().isoformat(timespec="seconds")
    rows = []
    for url in pages:
        try:
            try:
                r = a11y.run(url, describe=False)
            except Exception as e:  # one retry for a network timeout; anything else is reported as it is
                if "Timeout" not in str(e):
                    raise
                r = a11y.run(url, describe=False)
            if r["blocked"]:
                raise RuntimeError(f"site served a block or error page to the browser (HTTP {r['http_status']}); not scored")
            row = {"url": url, "before": r["before"], "after": r["after"], "verified": r["verified"],
                   "resolved": r["resolved"], "failed_recheck": sum(f["status"] == "failed re-check" for f in r["fixes"]),
                   "rolled_back": sum(f["status"] == "rolled back" for f in r["fixes"]),
                   "new_problems": len(r["new_problems"]), "error": ""}
        except Exception as e:
            row = {"url": url, "before": "", "after": "", "verified": "", "resolved": "", "failed_recheck": "", "rolled_back": "", "new_problems": "",
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
          f" · fixes proven {sum(r['verified'] for r in ok)} · also resolved {sum(r['resolved'] for r in ok)} · failed re-check {sum(r['failed_recheck'] for r in ok)}"
          f" · new problems {sum(r['new_problems'] for r in ok)}")
