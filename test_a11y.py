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
    assert unfixed == {"link-name"}  # a file:// page has no web address to name the icon link from
    alts = {f["value"] for f in r["fixes"] if f["rule"] == "image-alt"}
    assert alts == {"SkyTrips", "Goa from Rs 2,999"}  # from the text inside each SVG image
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
    assert r["before"] == 12 and r["after"] == 0 and r["verified"] == 12
    assert r["new_problems"] == []
    sources = {f["rule"]: f["source"] for f in r["fixes"]}
    assert "icon class" in sources["button-name"]
    imgs = {f["html"]: f for f in r["fixes"] if f["rule"] == "image-alt"}
    linked = next(f for h, f in imgs.items() if 'width="80"' in h)
    assert linked["value"] == "example.org" and "where its link goes" in linked["source"]  # never decorative
    thin = next(f for h, f in imgs.items() if "top_corner_left" in h)
    assert thin["value"] == "" and "decorative" in thin["source"]
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
    assert r["verified"] == 8  # only the bad fix is undone; the other eight stay proven


def test_slideshow_text_is_skipped_not_failed():
    page = (pathlib.Path(__file__).parent / "demo/carousel.html").resolve().as_uri()
    r = a11y.run(page, describe=False)
    by_text = {f["html"]: f for f in r["fixes"] if f["rule"] == "color-contrast"}
    moving = next(f for h, f in by_text.items() if "Moving slide" in h)
    still = next(f for h, f in by_text.items() if "Still text" in h)
    assert moving["status"] == "not fixed" and "slideshow" in moving["why"]
    assert still["status"] == "verified"
    assert not any(f["status"] == "failed re-check" for f in r["fixes"])


def test_server_refuses_private_addresses_and_serves_live_fix_script(monkeypatch):
    from fastapi.testclient import TestClient
    import server
    calls = []
    monkeypatch.setattr(server.a11y, "run", lambda url: calls.append(url) or {"fix_script": "/* Ctrl+A11y fixes for x: 7 fixes, each proven by re-check */"})
    server.live_cache.clear()
    c = TestClient(server.app)
    for bad in ["http://127.0.0.1:22/", "http://10.0.0.5/", "http://169.254.169.254/latest/meta-data/", "ftp://example.com/"]:
        assert c.post("/api/run", json={"url": bad}).status_code == 400, bad
    # The server's own host is allowed, so the demo pages work; the bookmarklet endpoint returns a script.
    r = c.get("/api/fix.js", params={"url": "http://testserver/demo/broken.html"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/javascript")
    assert r.headers["access-control-allow-origin"] == "*"
    assert "proven by re-check" in r.text
    c.get("/api/fix.js", params={"url": "http://testserver/demo/broken.html"})
    assert calls == ["http://testserver/demo/broken.html"]  # second request served from cache
    assert "console.warn" in c.get("/api/fix.js", params={"url": "http://10.0.0.5/"}).text  # refused, but as harmless JS
    spoken = c.get("/api/fix.js", params={"url": "http://testserver/demo/broken.html", "announce": 1}).text
    assert "applied \" + 7 + \" proven" in spoken.replace("COUNT", "")  # screen-reader message carries the count


def test_wrapped_page_keeps_header_footer_and_hidden_buttons():
    """Lessons from mygov.in and vtu.ac.in: main must not swallow the header, a role=presentation button is not
    named (that creates new problems), and a block named "footer" is not made a second footer."""
    r = a11y.run(DEMO.replace("broken.html", "wrapped.html"), describe=False)
    assert r["new_problems"] == []
    by = {(f["rule"], f["target"]): f for f in r["fixes"]}
    assert by[("landmark-one-main", "html")]["fix_target"] == "#content"
    assert by[("button-name", "button")]["status"] == "not fixed"
    assert by[("region", ".site-footer")]["status"] == "not fixed"
    assert not any(f["status"] in ("rolled back", "failed re-check") for f in r["fixes"])
    assert by[("aria-command-name", ".bi")]["value"] == "Share"
    assert by[("aria-command-name", ".marker")]["status"] == "not fixed"
