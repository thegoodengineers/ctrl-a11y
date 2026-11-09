"""The one check that matters: on the planted demo page, every fix we claim is proven by the re-audit,
nothing new breaks, and what we can't fix is reported, not hidden."""
import pathlib

import a11y

DEMO = (pathlib.Path(__file__).parent / "demo/broken.html").resolve().as_uri()


def test_demo_page_fixes_are_verified_and_honest():
    r = a11y.run(DEMO, describe=False)
    assert r["before"] == 10
    assert r["new_problems"] == []
    assert all(f["status"] in ("verified", "not fixed") for f in r["fixes"])  # no "failed re-check"
    assert r["after"] == r["before"] - r["verified"]
    unfixed = {f["rule"] for f in r["fixes"] if f["status"] == "not fixed"}
    assert unfixed == {"image-alt", "link-name"}  # need the AI step, which is off here
    assert 'lang="en"' in r["patched_html"]


def test_fix_script_on_original_page_gives_same_result():
    """The script a site owner would ship must reproduce the engine's proven result on the untouched page."""
    from playwright.sync_api import sync_playwright
    r = a11y.run(DEMO, describe=False)
    with sync_playwright() as p:
        b = p.chromium.launch(); page = b.new_page(); page.goto(DEMO)
        page.add_script_tag(content=r["fix_script"])
        left = a11y._audit(page)
        b.close()
    assert len(left) == r["after"]
    for f in r["fixes"]:  # every proven fix's element is in the script
        if f["status"] == "verified":
            assert (f.get("fix_target") or f["target"]).replace('"', '\\"') in r["fix_script"]


def test_second_fixer_set_all_proven_and_script_reproduces():
    from playwright.sync_api import sync_playwright
    page_url = (pathlib.Path(__file__).parent / "demo/more.html").resolve().as_uri()
    r = a11y.run(page_url, describe=False)
    assert r["before"] == 9 and r["after"] == 0 and r["verified"] == 9
    assert r["new_problems"] == []
    sources = {f["rule"]: f["source"] for f in r["fixes"]}
    assert "icon class" in sources["button-name"] and "link address" in sources["link-name"]
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(); pg.goto(page_url)
        pg.add_script_tag(content=r["fix_script"]); left = a11y._audit(pg); b.close()
    assert left == []


def test_a_fix_that_creates_a_new_problem_is_rolled_back(monkeypatch):
    """Sabotage one fixer so it writes an invalid language code. The safety net must undo it."""
    bad = a11y.FIX_JS.replace('return set("lang", "en");', 'return set("lang", "xx-not-a-language");')
    assert bad != a11y.FIX_JS
    monkeypatch.setattr(a11y, "FIX_JS", bad)
    r = a11y.run(DEMO, describe=False)
    assert r["new_problems"] == []
    lang = next(f for f in r["fixes"] if f["rule"] == "html-has-lang")
    assert lang["status"] == "rolled back" and "new problem" in lang["why"]
    assert "xx-not-a-language" not in r["fix_script"]
    assert r["verified"] == 6  # only the bad fix is undone; the other six stay proven


def test_slideshow_text_is_skipped_not_failed():
    page = (pathlib.Path(__file__).parent / "demo/carousel.html").resolve().as_uri()
    r = a11y.run(page, describe=False)
    by_text = {f["html"]: f for f in r["fixes"] if f["rule"] == "color-contrast"}
    moving = next(f for h, f in by_text.items() if "Moving slide" in h)
    still = next(f for h, f in by_text.items() if "Still text" in h)
    assert moving["status"] == "not fixed" and "slideshow" in moving["why"]
    assert still["status"] == "verified"
    assert not any(f["status"] == "failed re-check" for f in r["fixes"])
