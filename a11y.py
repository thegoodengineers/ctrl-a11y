"""Ctrl+A11y engine: audit a page with axe-core, fix what can be fixed, re-audit to prove it.

A fix only counts as verified if, on the re-audit, the same rule no longer flags the same element.
Anything the engine cannot fix honestly is reported as "needs a human", never guessed.
"""
import base64
import os
import pathlib

from playwright.sync_api import sync_playwright

AXE = (pathlib.Path(__file__).parent / "node_modules/axe-core/axe.min.js").read_text(encoding="utf-8")

# Pages that are really a bot-block or error page, not the site. We report these, never score them.
BLOCK_WORDS = ("access denied", "403 forbidden", "request blocked", "are you a robot", "verify you are human",
               "captcha", "attention required", "just a moment")

# Rules we try to fix. Everything else is reported, not touched.
NAME_RULES = {"image-alt", "input-image-alt", "button-name", "link-name"}  # need a name from what the element shows
FIXABLE = NAME_RULES | {"label", "select-name", "html-has-lang", "document-title", "color-contrast", "frame-title",
                        "region", "landmark-one-main", "aria-required-parent", "aria-required-children",
                        "tabindex", "link-in-text-block"}

# Deterministic fixers, run inside the page. Each returns {"value": ...} when it changed something,
# or {"skip": reason} when it can't fix the element honestly.
FIX_JS = r"""
([rule, selector, extra]) => {
  const el = document.querySelector(selector);
  if (!el) return {skip: "element not found"};
  const human = s => (s || "").replace(/[-_]+/g, " ").replace(/([a-z])([A-Z])/g, "$1 $2").replace(/\s+/g, " ").trim();
  const cap = s => s ? s[0].toUpperCase() + s.slice(1) : s;
  const set = (attr, v, source) => { el.setAttribute(attr, v); return {attr, value: v, source}; };
  // A stable CSS path for an element we change that axe didn't point at (used by the fix script).
  const path = n => {
    const parts = [];
    while (n && n.nodeType === 1 && n !== document.documentElement) {
      if (n.id && /^[A-Za-z][\w-]*$/.test(n.id)) { parts.unshift("#" + n.id); break; }
      let i = 1, s = n; while ((s = s.previousElementSibling)) if (s.tagName === n.tagName) i++;
      parts.unshift(n.tagName.toLowerCase() + ":nth-of-type(" + i + ")"); n = n.parentElement;
    }
    return parts.join(" > ") || "html";
  };
  // Where a name can honestly come from, in order of trust. Returns [name, source] or null.
  const nameClue = () => {
    const t = el.getAttribute("title") || el.getAttribute("value");
    if (t && t.trim()) return [t.trim(), "its own title"];
    const svgT = el.querySelector("svg title"); if (svgT && svgT.textContent.trim()) return [svgT.textContent.trim(), "its icon's title"];
    const img = el.querySelector("img[alt]:not([alt=''])"); if (img) return [img.getAttribute("alt").trim(), "its image's description"];
    const mat = el.querySelector(".material-icons, .material-symbols-outlined, .material-symbols-rounded");
    if (mat && /^[a-z_]+$/.test(mat.textContent.trim())) return [cap(human(mat.textContent.trim())), "its icon name"];
    const cls = [el, ...el.querySelectorAll("[class]")].map(n => n.getAttribute("class") || "").join(" ");
    const icon = cls.match(/(?:^|\s)(?:fa|fas|far|fab|bi|icon|glyphicon|mdi|ti|lni|ri)[-_]([a-z][a-z0-9-]*)/i);
    if (icon && !/^(lg|xs|sm|[0-9]x|fw|solid|regular|brands|light|duotone|spin|pulse|inverse|stack|icon)$/i.test(icon[1]))
      return [cap(human(icon[1])), "its icon class"];
    if (el.tagName === "A" && el.getAttribute("href")) {
      try {
        const u = new URL(el.getAttribute("href"), location.href);
        if (!/^https?:$/.test(u.protocol)) return null;
        if (u.hostname !== location.hostname) return [u.hostname.replace(/^www\./, ""), "the link address"];
        const seg = u.pathname.split("/").filter(Boolean).pop();
        if (!seg) return ["Home", "the link address"];
        const word = human(decodeURIComponent(seg).replace(/\.[a-z0-9]+$/i, ""));
        if (/^[a-z][a-z\s]{2,}$/i.test(word)) return [cap(word), "the link address"];
      } catch (e) { return null; }
    }
    return null;
  };

  if (rule === "image-alt" || rule === "input-image-alt") {
    if (extra === "") return set("alt", "", "judged decorative by the vision model");
    if (extra) return set("alt", extra, "the vision model");
    const w = el.naturalWidth || el.width, h = el.naturalHeight || el.height;
    const file = (el.getAttribute("src") || "").split(/[?#]/)[0].split("/").pop().toLowerCase();
    if ((w && h && w <= 16 && h <= 16) || /(spacer|blank|pixel|shim|clear|transparent|border|corner|divider|dot)[^/]*\.(gif|png|jpe?g|svg|webp)$/.test(file))
      return set("alt", "", "a tiny spacer or border graphic, so marked decorative");
    const link = el.closest("a[title], a[aria-label], button[title], button[aria-label]");
    if (link) { const t = (link.getAttribute("aria-label") || link.getAttribute("title")).trim(); if (t) return set("alt", t, "the link around it"); }
    const cap2 = el.closest("figure") && el.closest("figure").querySelector("figcaption");
    if (cap2 && cap2.textContent.trim()) return set("alt", cap2.textContent.trim().slice(0, 120), "its caption");
    if (el.getAttribute("title")) return set("alt", el.getAttribute("title").trim(), "its own title");
    return {skip: "no honest clue to describe it; needs the vision model or a person"};
  }
  if (rule === "button-name" || rule === "link-name") {
    if (extra) return set("aria-label", extra, "the vision model");
    const c = nameClue();
    if (!c) return {skip: "no honest clue to name it from; needs the vision model or a person"};
    return set("aria-label", c[0], c[1]);
  }
  if (rule === "label" || rule === "select-name") {
    let name = el.getAttribute("placeholder") || el.getAttribute("title") ||
               human(el.getAttribute("name")) || human(el.id), source = "its placeholder, name or id";
    if (!name && el.tagName === "SELECT" && el.options.length) {
      const first = el.options[0].textContent.trim();
      if (first && !/^[\d\s.,-]+$/.test(first)) { name = first.replace(/[.:…]+$/, ""); source = "its first option"; }
    }
    if (!name) return {skip: "no placeholder, name or id to label it from"};
    return set("aria-label", name, source);
  }
  if (rule === "tabindex") return set("tabindex", "0", "positive tab order replaced so keyboard order follows the page");
  if (rule === "link-in-text-block") {
    el.style.setProperty("text-decoration", "underline", "important");
    return {attr: "style.text-decoration", value: "underline", source: "links in text must not rely on colour alone"};
  }
  if (rule === "aria-required-parent" || rule === "aria-required-children") {
    const role = el.getAttribute("role");
    if (!role) return {skip: "no explicit role to remove"};
    el.removeAttribute("role");
    return {attr: "role", value: null, source: `role "${role}" was used without the structure it requires; no ARIA beats bad ARIA`};
  }
  if (rule === "region" || rule === "landmark-one-main") {
    let main = document.querySelector("main, [role=main]");
    if (!main) {
      const skip = n => /^(HEADER|NAV|FOOTER|ASIDE)$/.test(n.tagName) || /^(banner|navigation|contentinfo|complementary)$/.test(n.getAttribute("role") || "");
      const kids = [...document.body.children].filter(n => !skip(n) && !/^(SCRIPT|STYLE|NOSCRIPT|TEMPLATE)$/.test(n.tagName));
      const h1 = document.querySelector("h1");
      const block = n => /^(DIV|SECTION|ARTICLE|FORM|TABLE|CENTER)$/.test(n.tagName);  // never a heading or inline element
      let pick = h1 && kids.find(k => k.contains(h1) && block(k));
      if (!pick) pick = kids.filter(block).sort((a, b) => (b.innerText || "").length - (a.innerText || "").length)[0];
      if (!pick) return {skip: "the content isn't wrapped in a block; a person must add a <main> element"};
      pick.setAttribute("role", "main"); main = pick;
      return {attr: "role", value: "main", target: path(pick), source: "marked the block holding the page's main content as the main area"};
    }
    if (rule === "region" && main.contains(el)) return {attr: "role", value: "main", target: path(main), source: "now inside the main area"};
    if (rule === "region") {
      // Content outside main: if its top-level block names itself clearly, give it that landmark.
      let top = el; while (top.parentElement && top.parentElement !== document.body) top = top.parentElement;
      const nameOf = ((top.id || "") + " " + (top.getAttribute("class") || "")).toLowerCase();
      if (top.getAttribute("role")) return {skip: "inside a block that already has a role; a person must decide"};
      let role = null;
      if (/(^|[\s_-])(nav|navbar|navigation|menu|menubar)([\s_-]|$)/.test(nameOf)) role = "navigation";
      else if (/(^|[\s_-])(header|masthead|topbar|top|banner|site-header)([\s_-]|$)/.test(nameOf)) role = "banner";
      else if (/(^|[\s_-])(footer|site-footer|bottom)([\s_-]|$)/.test(nameOf)) role = "contentinfo";
      if (!role || document.querySelector(`[role=${role}]`) && role !== "navigation")
        return {skip: "content outside every landmark; a person must decide which landmark it belongs to"};
      top.setAttribute("role", role);
      return {attr: "role", value: role, target: path(top), source: `its block is named "${nameOf.trim()}", so marked as ${role}`};
    }
    return {skip: "content outside every landmark; a person must decide which landmark it belongs to"};
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
        resp = page.goto(url, wait_until="load", timeout=30000)
        status = resp.status if resp else None
        head = (page.title() + " " + page.evaluate("() => (document.body ? document.body.innerText : '').slice(0, 400)")).lower()
        blocked = bool(status and status >= 400) or any(w in head for w in BLOCK_WORDS)
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
                shown = "removed" if r["value"] is None else f'"{r["value"]}"'
                fixes.append({**v, "status": "applied", "attr": r["attr"], "value": r["value"],
                              "fix_target": r.get("target") or v["target"], "source": r.get("source", ""),
                              "change": f'{r["attr"]} = {shown}' + (f' (from {r["source"]})' if r.get("source") else "")})

        after = _audit(page)
        still = {(a["rule"], a["target"]) for a in after}
        for f in fixes:
            if f["status"] == "applied":
                f["status"] = "verified" if (f["rule"], f["target"]) not in still else "failed re-check"
        before_keys = {(b["rule"], b["target"]) for b in before}
        new = [a for a in after if (a["rule"], a["target"]) not in before_keys]

        # Safety net: a fix must never leave the page worse. If the re-check found new problems, rebuild the page
        # from the original with fewer fixes (first without structural role changes, then with none) and re-check.
        if new:
            structural = {"region", "landmark-one-main", "aria-required-parent", "aria-required-children"}
            applied_rules = sorted({f["rule"] for f in fixes if f["status"] in ("verified", "failed re-check")},
                                   key=lambda r: (r not in structural, r))  # riskiest first
            candidates = [{r} for r in applied_rules] + [structural, None]  # undo one kind, then all structural, then all
            first_pass = {id(f): f["status"] for f in fixes}
            for dropped in candidates:
                keep = [f for f in fixes if first_pass[id(f)] == "verified" and dropped is not None and f["rule"] not in dropped]
                page.goto(url, wait_until="load", timeout=30000)
                if keep:
                    page.add_script_tag(content=fix_script(url, keep, only_verified=False))
                after = _audit(page)
                still = {(a["rule"], a["target"]) for a in after}
                new = [a for a in after if (a["rule"], a["target"]) not in before_keys]
                for f in fixes:
                    if first_pass[id(f)] in ("verified", "failed re-check"):
                        if f in keep:
                            f["status"] = "verified" if (f["rule"], f["target"]) not in still else "failed re-check"
                            f.pop("why", None)
                        else:
                            f["status"] = "rolled back"
                            f["why"] = "undone automatically: with it applied, the re-check found a new problem"
                if not new:
                    break

        result = {
            "url": url, "http_status": status, "blocked": blocked,
            "before": len(before), "after": len(after),
            "verified": sum(f["status"] == "verified" for f in fixes),
            "new_problems": new,
            "fixes": fixes,
            "reader_before": reader_before,
            "reader_after": page.locator("body").aria_snapshot(),
            "patched_html": page.content(),
            "fix_script": fix_script(url, fixes),
        }
        browser.close()
        return result


def fix_script(url, fixes, only_verified=True):
    """One script a site owner adds to the page to apply every PROVEN fix. Unproven fixes are left out."""
    import json
    proven = []
    for f in fixes:
        if f["status"] == "verified" or not only_verified:
            entry = [f.get("fix_target") or f["target"], f["attr"], f["value"]]
            if entry not in proven:  # one landmark fix can resolve many problems; apply it once
                proven.append(entry)
    return (f"/* Ctrl+A11y fixes for {url}: {len(proven)} fixes, each proven by re-check. "
            f"Add before </body>: <script src=\"ctrl-a11y-fixes.js\"></script> */\n"
            "(function () {\n"
            f"  var fixes = {json.dumps(proven, ensure_ascii=False)};\n"
            "  function apply() {\n"
            "    fixes.forEach(function (f) {\n"
            "      var el = document.querySelector(f[0]);\n"
            "      if (!el) return;\n"
            "      if (f[1] === 'title' && el === document.documentElement) document.title = f[2];\n"
            "      else if (f[1].indexOf('style.') === 0) el.style.setProperty(f[1].slice(6), f[2], 'important');\n"
            "      else if (f[2] === null) el.removeAttribute(f[1]);\n"
            "      else el.setAttribute(f[1], f[2]);\n"
            "    });\n"
            "  }\n"
            "  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', apply); else apply();\n"
            "})();\n")


if __name__ == "__main__":
    import json, sys
    r = run(sys.argv[1], describe="--no-ai" not in sys.argv)
    print(json.dumps({k: r[k] for k in ("url", "before", "after", "verified")}, indent=2))
    for f in r["fixes"]:
        print(f'{f["status"]:16} {f["rule"]:16} {f["target"][:40]:40} {f.get("change") or f.get("why", "")}')
    print("new problems introduced:", len(r["new_problems"]))
