"""Take the Devpost screenshots from the real app: python docs/shots.py  ->  docs/screenshots/*.png (1440 px wide).
Starts its own server on port 8791, so nothing else needs to be running."""
import pathlib
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"
APP = "http://localhost:8791"
DEMO = APP + "/demo/broken.html"
REAL = "https://news.ycombinator.com/"


def at(page, selector, name, offset=40):
    """Scroll an element to near the top and save the visible window."""
    page.evaluate("([s, o]) => { const e = document.querySelector(s); scrollTo(0, e.getBoundingClientRect().top + scrollY - o); }",
                  [selector, offset])
    page.wait_for_timeout(400)
    page.screenshot(path=str(OUT / name))
    print("saved", name)


def check(page, url):
    page.goto(APP, wait_until="networkidle")
    page.fill("#url", url)
    page.click("#go")
    page.wait_for_selector("#out:not([hidden])", timeout=180000)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "server:app", "--port", "8791"], cwd=ROOT,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen(APP, timeout=1); break
            except OSError:
                time.sleep(0.5)
        with sync_playwright() as p:
            page = p.chromium.launch().new_page(viewport={"width": 1440, "height": 900})
            page.goto(APP, wait_until="networkidle"); page.wait_for_timeout(800)
            page.screenshot(path=str(OUT / "01-paste-a-url.png")); print("saved 01-paste-a-url.png")
            check(page, DEMO)
            at(page, "#h-res", "02-result.png")
            at(page, "#h-proven", "03-fixed-and-proven.png")
            at(page, "#h-person", "04-needs-a-person.png")
            at(page, "#rb", "05-screen-reader-before-after.png", 160)
            at(page, "#sb", "06-see-the-difference.png", 160)
            at(page, ".ship", "07-ship-the-fixes.png", 160)
            check(page, REAL)
            at(page, "#h-res", "08-real-site-hacker-news.png")
    finally:
        server.terminate()
