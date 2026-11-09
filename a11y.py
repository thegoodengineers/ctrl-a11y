"""Ctrl+A11y engine: audit a page with axe-core, fix what can be fixed, re-audit to prove it.

A fix only counts as verified if, on the re-audit, the same rule no longer flags the same element.
Anything the engine cannot fix honestly is reported as "needs a human", never guessed.
"""
import base64
import os
import pathlib

from playwright.sync_api import sync_playwright

AXE = (pathlib.Path(__file__).parent / "node_modules/axe-core/axe.min.js").read_text(encoding="utf-8")

# Rules we try to fix. Everything else is reported, not touched.
NAME_RULES = {"image-alt", "input-image-alt", "button-name", "link-name"}  # need a name from what the element shows
FIXABLE = NAME_RULES | {"label", "select-name", "html-has-lang", "document-title", "color-contrast", "frame-title"}

# Deterministic fixers, run inside the page. Each returns {"value": ...} when it changed something,
# or {"skip": reason} when it can't fix the element honestly.
FIX_JS = r"""
([rule, selector, extra]) => {
  const el = document.querySelector(selector);
  if (!el) return {skip: "element not found"};
  const human = s => (s || "").replace(/[-_]+/g, " ").replace(/([a-z])([A-Z])/g, "$1 $2").trim();
  const set = (attr, v) => { el.setAttribute(attr, v); return {attr, value: v}; };

  if (rule === "image-alt" || rule === "input-image-alt" || rule === "button-name" || rule === "link-name") {
    const isImg = rule === "image-alt" || rule === "input-image-alt";
    const own = el.getAttribute("title") || el.getAttribute("value");
    const name = extra ?? own;
    if (isImg && name === "") return set("alt", "");  // AI judged it decorative: empty alt is the correct fix
    if (!name) return {skip: "no visible clue to name it from"};
    return isImg ? set("alt", name) : set("aria-label", name);
  }
  if (rule === "label" || rule === "select-name") {
    const name = el.getAttribute("placeholder") || el.getAttribute("title") ||
                 human(el.getAttribute("name")) || human(el.id);
    if (!name) return {skip: "no placeholder, name or id to label it from"};
    return set("aria-label", name);
  }
  if (rule === "html-has-lang") {
    const text = document.body ? document.body.innerText : "";
    const ascii = text.replace(/[^\x00-\x7F]/g, "").length / Math.max(text.length, 1);
    if (ascii < 0.95) return {skip: "page is not clearly English; language must be set by a person"};
    return set("lang", "en");
  }
  if (rule === "document-title") {
    const h1 = document.querySelector("h1");
    if (!h1 || !h1.innerText.trim()) return {skip: "no main heading to title the page from"};
    document.title = h1.innerText.trim();
    return {attr: "title", value: document.title};
  }
  if (rule === "frame-title") {
    try { return set("title", "Embedded content from " + new URL(el.src).hostname); }
    catch (e) { return {skip: "frame has no usable source"}; }
  }
  if (rule === "color-contrast") {
    // extra = {fg, bg, ratio} from axe. Move the text colour towards black or white until it passes.
    const parse = c => {
      if (c[0] === "#") {
        const h = c.length === 4 ? [...c.slice(1)].map(x => x + x).join("") : c.slice(1, 7);
        return [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16));
      }
      return c.match(/[\d.]+/g).slice(0, 3).map(Number);
    };
    const lum = ([r, g, b]) => {
      const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
      return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
    };
    const contrast = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
    if (!extra || !extra.fg || !extra.bg) return {skip: "colours not known (image or gradient background)"};
    // Text inside a fading or rotating slideshow: colours are measured mid-fade and the slide changes before
    // the re-check, so no fix can be proven. Say so instead of applying one.
    const stateful = /(active|current|selected)[^\s>]*(slide|item)|(slide|item)[^\s>]*(active|current|selected)/i.test(selector);
    let fading = false;
    for (let a = el; a && a !== document.body; a = a.parentElement) {
      if (parseFloat(getComputedStyle(a).opacity) < 1) { fading = true; break; }
    }
    if (stateful || fading) return {skip: "inside a moving slideshow; contrast can't be fixed and proven while it animates, needs a person"};
    const fg = parse(extra.fg), bg = parse(extra.bg), target = (extra.ratio || 4.5) + 0.1;
    const toward = lum(bg) > 0.18 ? [0, 0, 0] : [255, 255, 255];
    for (let t = 0; t <= 1.0001; t += 0.02) {
      const c = fg.map((v, i) => Math.round(v + (toward[i] - v) * t));
      if (contrast(c, bg) >= target) {
        const v = `rgb(${c.join(", ")})`;
        el.style.setProperty("color", v, "important");
        return {attr: "style.color", value: v};
      }
    }
    return {skip: "no text colour reaches the required contrast on this background"};
  }
  return {skip: "rule not handled"};
}
"""


def _audit(page):
    page.evaluate(AXE)
    result = page.evaluate("() => axe.run(document, {resultTypes: ['violations']})")
    return [
        {"rule": v["id"], "impact": v["impact"], "help": v["help"],
         "target": " ".join(n["target"]) if all(isinstance(t, str) for t in n["target"]) else str(n["target"]),
         "html": n["html"][:200], "data": (n.get("any") or [{}])[0].get("data")}
        for v in result["violations"] for n in v["nodes"]
    ]


def _describe(page, target, rule):
    """Ask the vision model for a short accessible name, from a screenshot of the element. None if unavailable."""
    if not (os.environ.get("CTRL_A11Y_ANTHROPIC_API_KEY") and os.environ.get("CTRL_A11Y_MODEL")):
        return None
    try:
        shot = page.locator(target).first.screenshot(timeout=3000)
    except Exception:
        return None
    import anthropic
    ask = ("Write alt text for this image: one short sentence, no 'image of'. If it is purely decorative, reply DECORATIVE."
           if rule in ("image-alt", "input-image-alt") else
           "This is a button or link with no text. Reply with a 1-4 word accessible name for what it does (e.g. 'Search', 'Open menu').")
    try:
        msg = anthropic.Anthropic(api_key=os.environ["CTRL_A11Y_ANTHROPIC_API_KEY"]).beta.messages.create(
            model=os.environ["CTRL_A11Y_MODEL"], max_tokens=1000,
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png",
                                             "data": base64.standard_b64encode(shot).decode()}},
                {"type": "text", "text": ask}]}],
        )
    except anthropic.APIError:  # bad key, rate limit, outage: leave it for a person, don't crash the run
        return None
    if msg.stop_reason == "refusal":
        return None
    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    return "" if text == "DECORATIVE" else (text or None)


def run(url, describe=True):
    """Audit, fix, re-audit. Returns before/after violations, every fix with its proof, and both screen-reader views."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="load", timeout=30000)
        before = _audit(page)
        reader_before = page.locator("body").aria_snapshot()

        fixes = []
        for v in before:
            if v["rule"] not in FIXABLE:
                fixes.append({**v, "status": "not fixed", "why": "needs a person (rule not auto-fixable)"})
                continue
            extra = None
            if v["rule"] in NAME_RULES and describe:
                extra = _describe(page, v["target"], v["rule"])
            if v["rule"] == "color-contrast" and v["data"]:
                d = v["data"]
                extra = {"fg": d.get("fgColor"), "bg": d.get("bgColor"), "ratio": d.get("expectedContrastRatio") and float(str(d["expectedContrastRatio"]).split(":")[0])}
            try:
                r = page.evaluate(FIX_JS, [v["rule"], v["target"], extra])
            except Exception as e:  # one bad element must not stop the run
                r = {"skip": f"fixer error: {str(e).splitlines()[0][:80]}"}
            if "skip" in r:
                fixes.append({**v, "status": "not fixed", "why": r["skip"]})
            else:
                fixes.append({**v, "status": "applied", "change": f'{r["attr"]} = "{r["value"]}"'})

        after = _audit(page)
        still = {(a["rule"], a["target"]) for a in after}
        for f in fixes:
            if f["status"] == "applied":
                f["status"] = "verified" if (f["rule"], f["target"]) not in still else "failed re-check"
        before_keys = {(b["rule"], b["target"]) for b in before}
        new = [a for a in after if (a["rule"], a["target"]) not in before_keys]

        result = {
            "url": url,
            "before": len(before), "after": len(after),
            "verified": sum(f["status"] == "verified" for f in fixes),
            "new_problems": new,
            "fixes": fixes,
            "reader_before": reader_before,
            "reader_after": page.locator("body").aria_snapshot(),
            "patched_html": page.content(),
        }
        browser.close()
        return result


if __name__ == "__main__":
    import json, sys
    r = run(sys.argv[1], describe="--no-ai" not in sys.argv)
    print(json.dumps({k: r[k] for k in ("url", "before", "after", "verified")}, indent=2))
    for f in r["fixes"]:
        print(f'{f["status"]:16} {f["rule"]:16} {f["target"][:40]:40} {f.get("change") or f.get("why", "")}')
    print("new problems introduced:", len(r["new_problems"]))
