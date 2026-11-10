"""Record every scene of video/script.md at 1280x720 for exactly its narration length (plus a short pause).

Cards come from video/scenes.html; app scenes drive the real app at http://localhost:8765 (start it first:
`python -m uvicorn server:app --port 8765`). Run narrate.py first so the clip lengths are known.
Output: video/renders/NN.webm and video/renders/offsets.json (where each clip's content starts).
"""
import json
import pathlib
import subprocess
import time

from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
APP = "http://localhost:8765"
SIZE = {"width": 1280, "height": 720}
PAUSE = 1.2
DEMO = APP + "/demo/broken.html"
REAL = "https://news.ycombinator.com/"
INDIA = "https://www.myscheme.gov.in/"


def lines():
    out = []
    for row in (HERE / "script.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[0].isdigit():
            out.append((int(cells[0]), cells[1]))
    return out


def seconds(n):
    mp3 = HERE / "vo" / f"{n:02}.mp3"
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)],
                                capture_output=True, text=True).stdout.strip())


def glide(page, selector, ms=1400):
    """Smoothly bring an element to the top third of the screen."""
    page.evaluate("""([s, ms]) => { const el = document.querySelector(s); if (!el) return;
        const y = el.getBoundingClientRect().top + scrollY - 120, from = scrollY, t0 = performance.now();
        const step = t => { const k = Math.min(1, (t - t0) / ms), e = k < .5 ? 2*k*k : 1 - Math.pow(-2*k + 2, 2) / 2;
          scrollTo(0, from + (y - from) * e); if (k < 1) requestAnimationFrame(step); }; requestAnimationFrame(step); }""", [selector, ms])
    page.wait_for_timeout(ms + 100)


def run_app(page, url):
    page.goto(APP, wait_until="networkidle")
    page.fill("#url", url)
    page.click("#go")
    page.wait_for_selector("#out:not([hidden])", timeout=120000)


def warm():
    """Check the pages once before recording, so results come from the server's 10-minute cache and each
    scene shows a real result without a long wait on camera."""
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport=SIZE)
        run_app(pg, DEMO)
        run_app(pg, REAL)
        pg.click("#site-btn")
        pg.wait_for_function("() => document.getElementById('site-msg').textContent.startsWith('Done')", timeout=600000)
        run_app(pg, INDIA)
        b.close()


# What each app scene does on screen. Each gets the page and must leave the final frame looking right.
def app_paste(page):
    page.goto(APP, wait_until="networkidle"); page.wait_for_timeout(900)
    page.evaluate("""(u) => { const d = new DataTransfer(); d.setData('text', u);
        document.body.dispatchEvent(new ClipboardEvent('paste', {clipboardData: d, bubbles: true})); }""", DEMO)
    page.wait_for_selector("#out:not([hidden])", timeout=120000); page.evaluate("scrollTo(0, 0)")
    page.wait_for_timeout(1500); glide(page, "#h-res", 1800)

def app_result(page):
    run_app(page, DEMO); glide(page, "#h-res", 10)

def app_fixes(page):
    run_app(page, DEMO); glide(page, "#h-res", 10); page.wait_for_timeout(800); glide(page, "#h-proven", 2600)
    page.wait_for_timeout(1800); glide(page, "#h-person", 2600)

def app_reader(page):
    run_app(page, DEMO); glide(page, "#rb", 10)

def hide_thumbnails(page):
    # Live third-party pages can show anything in their headlines; keep their thumbnails out of the video.
    page.evaluate("() => document.getElementById('sb').closest('.panel').style.display = 'none'")

def app_real(page):
    run_app(page, REAL); hide_thumbnails(page); glide(page, "#h-res", 10)

def app_india(page):
    run_app(page, INDIA); glide(page, "#h-res", 10)

def app_site(page):
    run_app(page, REAL); hide_thumbnails(page); glide(page, "#site-wrap", 10); page.wait_for_timeout(600)
    page.click("#site-btn"); glide(page, "#site-wrap", 10)

def app_ship(page):
    run_app(page, DEMO); glide(page, ".ship", 10)

def app_bookmark(page):
    page.goto(APP, wait_until="networkidle"); glide(page, "#h-user", 1600); page.wait_for_timeout(2200)
    bookmark = page.get_attribute("#bm", "href")
    page.goto(DEMO, wait_until="load"); page.wait_for_timeout(700)
    page.evaluate(bookmark[len("javascript:"):])
    page.wait_for_function("() => { const s = document.querySelector('[role=status]'); return s && s.textContent; }", timeout=60000)
    said = page.evaluate("() => document.querySelector('[role=status]').textContent")
    # Show the spoken announcement on screen, since a recording can't show audio from a screen reader.
    page.evaluate("""(t) => { const d = document.createElement('div'); d.textContent = 'Screen reader: "' + t + '"';
        d.style.cssText = 'position:fixed;left:24px;right:24px;bottom:24px;padding:18px 22px;border-radius:14px;background:#17181a;color:#fff;font:600 24px system-ui';
        document.body.appendChild(d); }""", said)

APP_SCENES = {"paste": app_paste, "result": app_result, "fixes": app_fixes, "reader": app_reader, "real": app_real, "india": app_india,
              "site": app_site, "ship": app_ship, "bookmark": app_bookmark}


def main():
    (HERE / "renders").mkdir(exist_ok=True)
    print("warming the cache..."); warm()
    offsets = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for n, scene in lines():
            kind, name = scene.split(":")
            length = seconds(n) + PAUSE
            ctx = browser.new_context(viewport=SIZE, record_video_dir=str(HERE / "renders" / "tmp"), record_video_size=SIZE)
            page = ctx.new_page()
            t0 = time.time()
            if kind == "card":
                page.goto((HERE / "scenes.html").resolve().as_uri() + f"?scene={name}"); page.wait_for_timeout(200)
                start = time.time() - t0
            else:
                start = time.time() - t0 + 0.2
                APP_SCENES[name](page)
            # Hold the last frame until the narration ends.
            remaining = start + length - (time.time() - t0)
            if remaining > 0:
                page.wait_for_timeout(int(remaining * 1000))
            video = page.video
            ctx.close()
            target = HERE / "renders" / f"{n:02}.webm"
            pathlib.Path(video.path()).replace(target)
            # Cards: start at the first frame. App scenes: the scene's own actions are part of the story.
            offsets[n] = round(start if kind == "card" else max(0.0, start - 0.2), 2)
            print(f"scene {n} {scene}: {length:.1f}s")
    (HERE / "renders" / "offsets.json").write_text(json.dumps(offsets, indent=1))


if __name__ == "__main__":
    main()
