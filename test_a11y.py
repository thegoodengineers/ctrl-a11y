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


def test_slideshow_text_is_skipped_not_failed():
    page = (pathlib.Path(__file__).parent / "demo/carousel.html").resolve().as_uri()
    r = a11y.run(page, describe=False)
    by_text = {f["html"]: f for f in r["fixes"] if f["rule"] == "color-contrast"}
    moving = next(f for h, f in by_text.items() if "Moving slide" in h)
    still = next(f for h, f in by_text.items() if "Still text" in h)
    assert moving["status"] == "not fixed" and "slideshow" in moving["why"]
    assert still["status"] == "verified"
    assert not any(f["status"] == "failed re-check" for f in r["fixes"])
