"""Ctrl+A11y engine: audit a page with axe-core, fix what can be fixed, re-audit to prove it.

A fix only counts as verified if, on the re-audit, the same rule no longer flags the same element.
Anything the engine cannot fix honestly is reported as "needs a human", never guessed.
"""
import base64
import re
import os
import pathlib

from playwright.sync_api import sync_playwright

AXE = (pathlib.Path(__file__).parent / "node_modules/axe-core/axe.min.js").read_text(encoding="utf-8")

# Pages that are really a bot-block or error page, not the site. We report these, never score them.
BLOCK_WORDS = ("access denied", "403 forbidden", "request blocked", "are you a robot", "verify you are human",
               "captcha", "attention required", "just a moment")

# Rules we try to fix. Everything else is reported, not touched.
NAME_RULES = {"image-alt", "input-image-alt", "button-name", "link-name", "aria-command-name"}  # need a name from what the element shows
FIXABLE = NAME_RULES | {"label", "select-name", "html-has-lang", "document-title", "color-contrast", "frame-title",
                        "region", "landmark-one-main", "aria-required-parent", "aria-required-children",
                        "tabindex", "link-in-text-block"}

# Deterministic fixers, run inside the page. Each returns {"value": ...} when it changed something,
# or {"skip": reason} when it can't fix the element honestly.
FIX_JS = r"""
async ([rule, selector, extra]) => {
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
  const nameClue = (node = el) => {
    const t = node.getAttribute("title") || node.getAttribute("value");
    if (t && t.trim()) return [t.trim(), "its own title"];
    const svgT = node.querySelector("svg title"); if (svgT && svgT.textContent.trim()) return [svgT.textContent.trim(), "its icon's title"];
    const img = node.querySelector("img[alt]:not([alt=''])"); if (img) return [img.getAttribute("alt").trim(), "its image's description"];
    const mat = node.querySelector(".material-icons, .material-symbols-outlined, .material-symbols-rounded");
    if (mat && /^[a-z_]+$/.test(mat.textContent.trim())) return [cap(human(mat.textContent.trim())), "its icon name"];
    const cls = [node, ...node.querySelectorAll("[class]")].map(n => n.getAttribute("class") || "").join(" ");
    const icon = cls.match(/(?:^|\s)(?:fa|fas|far|fab|bi|icon|glyphicon|mdi|ti|lni|ri)[-_]([a-z][a-z0-9-]*)/i);
    if (icon && !/^(lg|xs|sm|[0-9]x|fw|solid|regular|brands|light|duotone|spin|pulse|inverse|stack|icon)$/i.test(icon[1]))
      return [cap(human(icon[1])), "its icon class"];
    if (node.tagName === "A" && node.getAttribute("href")) {
      try {
        let href = node.getAttribute("href");
        const js = href.match(/^javascript:\s*(?:window\.)?location(?:\.href)?\s*=\s*['"]([^'"]+)['"]/i);
        if (js) href = js[1];  // an old-style link that only navigates: use where it goes
        const u = new URL(href, location.href);
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
    // A linked image with no text IS the link's name, so it is never decorative; WCAG says it should say where
    // the link goes. Checked first, before any "looks decorative" rule.
    const parentLink = el.closest("a[href]");
    if (parentLink && !(parentLink.textContent || "").trim()) {
      const linkClue = nameClue(parentLink);
      if (linkClue) return set("alt", linkClue[0], "where its link goes");
      return {skip: "the only content of a link, with no clue where it goes; needs the vision model or a person"};
    }
    const box = el.getBoundingClientRect();  // judge size as shown on the page, not the file's own size
    const w = Math.round(box.width) || el.naturalWidth || el.width, h = Math.round(box.height) || el.naturalHeight || el.height;
    const file = (el.getAttribute("src") || "").split(/[?#]/)[0].split("/").pop().toLowerCase();
    if ((w && h && w <= 16 && h <= 16) || /(spacer|blank|pixel|shim|clear|transparent|border|corner|divider|dot)[^/]*\.(gif|png|jpe?g|svg|webp)$/.test(file))
      return set("alt", "", "a tiny spacer or border graphic, so marked decorative");
    const thin = w && h && Math.min(w, h) <= 30;
    if (thin && /(^|[_-])(end|left|right|top|bottom|bg|back|background|line|shadow|edge|corner|border|spacer|filler|cap|slice)([_.-]|$)/.test(file))
      return set("alt", "", "a thin layout slice of the page design, so marked decorative");
    const link = el.closest("a[title], a[aria-label], button[title], button[aria-label]");
    if (link) { const t = (link.getAttribute("aria-label") || link.getAttribute("title")).trim(); if (t) return set("alt", t, "the link around it"); }
    const cap2 = el.closest("figure") && el.closest("figure").querySelector("figcaption");
    if (cap2 && cap2.textContent.trim()) return set("alt", cap2.textContent.trim().slice(0, 120), "its caption");
    if (el.getAttribute("title")) return set("alt", el.getAttribute("title").trim(), "its own title");
    // An SVG image that contains real words (logos, banners): describe it with those words.
    const src = el.getAttribute("src") || "";
    if (/^data:image\/svg\+xml|\.svg(\?|#|$)/i.test(src)) {
      try {
        let markup;
        if (src.startsWith("data:")) {
          const body = src.slice(src.indexOf(",") + 1);
          markup = /;base64,/i.test(src.slice(0, src.indexOf(",") + 1)) ? atob(body) : decodeURIComponent(body);
        } else {
          markup = await (await fetch(new URL(src, location.href))).text();
        }
        const doc = new DOMParser().parseFromString(markup, "image/svg+xml");
        const words = [...doc.querySelectorAll("title, text")].map(n => n.textContent.trim()).filter(Boolean).join(" ").replace(/\s+/g, " ").trim();
        if (words.length >= 2 && /[a-z]/i.test(words)) return set("alt", words.slice(0, 150), "the text inside the image");
      } catch (e) { /* unreadable SVG: fall through to the honest skip */ }
    }
    return {skip: "no honest clue to describe it; needs the vision model or a person"};
  }
  if (rule === "button-name" || rule === "link-name" || rule === "aria-command-name") {  // last: role=button/link/menuitem
    if (/^(presentation|none)$/.test(el.getAttribute("role") || ""))
      return {skip: "it is hidden from screen readers with role presentation; a person must decide if it should be"};
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
      const h1 = document.querySelector("h1");
      const block = n => /^(DIV|SECTION|ARTICLE|FORM|TABLE|CENTER)$/.test(n.tagName);  // never a heading or inline element
      // A main area must not swallow the page header or footer (they'd stop being landmarks), so when the best
      // block wraps them, look one level deeper.
      const wrapsChrome = n => n.querySelector("header, footer, [role=banner], [role=contentinfo]");
      let parent = document.body, pick = null;
      for (let depth = 0; depth < 6 && !pick; depth++) {
        const kids = [...parent.children].filter(n => !skip(n) && block(n));
        const best = (h1 && kids.find(k => k.contains(h1))) ||
                     kids.sort((a, b) => (b.innerText || "").length - (a.innerText || "").length)[0];
        if (!best) break;
        if (wrapsChrome(best)) parent = best; else pick = best;
      }
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
      const existing = {banner: "header, [role=banner]", contentinfo: "footer, [role=contentinfo]"}[role];  // <footer> counts too
      if (!role || existing && document.querySelector(existing))
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
    for attempt in (1, 2):
        try:
            page.evaluate(AXE)
            result = page.evaluate("() => axe.run(document, {resultTypes: ['violations']})")
            break
        except Exception as e:  # the page redirected itself mid-check: wait for it to settle, check once more
            if attempt == 2 or "context was destroyed" not in str(e):
                raise
            page.wait_for_load_state("load", timeout=20000)
    return [
        {"rule": v["id"], "impact": v["impact"], "help": v["help"], "help_url": v.get("helpUrl", ""),
         "wcag": _wcag(v.get("tags", [])),
         "target": " ".join(n["target"]) if all(isinstance(t, str) for t in n["target"]) else str(n["target"]),
         "html": n["html"][:200], "data": (n.get("any") or [{}])[0].get("data")}
        for v in result["violations"] for n in v["nodes"]
    ]


def _shot(page):
    """Viewport screenshot as a small JPEG data URL, for the visual before/after."""
    try:
        return "data:image/jpeg;base64," + base64.standard_b64encode(page.screenshot(type="jpeg", quality=55)).decode()
    except Exception:
        return ""


# Up to 5 other pages on the same site, linked from this one, for the "check more of this site" step.
SITE_LINKS_JS = r"""
() => {
  const seen = new Set([location.href.split("#")[0]]), out = [];
  for (const a of document.querySelectorAll("a[href]")) {
    let u; try { u = new URL(a.getAttribute("href"), location.href); } catch (e) { continue; }
    if (u.origin !== location.origin || !/^https?:$/.test(u.protocol)) continue;
    if (/\.(pdf|zip|jpe?g|png|gif|svg|mp4|mp3|docx?|xlsx?)$/i.test(u.pathname)) continue;
    const key = u.origin + u.pathname + u.search;
    if (seen.has(key)) continue;
    seen.add(key); out.push(key);
    if (out.length === 5) break;
  }
  return out;
}
"""


def _wcag(tags):
    """axe tags like 'wcag143' -> WCAG success criteria like '1.4.3'. Best-practice rules have none."""
    import re
    out = []
    for t in tags:
        m = re.fullmatch(r"wcag(\d)(\d)(\d+)", t)
        if m and ".".join(m.groups()) not in out:
            out.append(".".join(m.groups()))
    return out


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


def _key(v):
    """Same problem on the same element. Random ids (swiper-wrapper-e819102eb6f1...) change on every load, so they
    are blanked out; otherwise a reload would look like a brand-new problem."""
    return v["rule"], re.sub(r"[0-9a-f]{8,}", "#", v["target"])


def _open(page, url):
    """Load the page and let late content (footers, hydration) settle, so every audit sees the same page."""
    resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
    for state, ms in (("load", 20000), ("networkidle", 5000)):
        try:
            page.wait_for_load_state(state, timeout=ms)
        except Exception:  # a slow image or a live ticker must not fail the check; audit what has loaded
            pass
    return resp


def run(url, describe=True):
    """Audit, fix, re-audit. Returns before/after violations, every fix with its proof, and both screen-reader views."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        # bypass_csp: strict Content-Security-Policy sites (digilocker, flipkart) otherwise refuse our injected scripts.
        page = browser.new_page(bypass_csp=True)
        resp = _open(page, url)
        status = resp.status if resp else None
        head = (page.title() + " " + page.evaluate("() => (document.body ? document.body.innerText : '').slice(0, 400)")).lower()
        blocked = bool(status and status >= 400) or any(w in head for w in BLOCK_WORDS)
        before = _audit(page)
        reader_before = page.locator("body").aria_snapshot()
        shot_before = _shot(page)
        site_links = page.evaluate(SITE_LINKS_JS)

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
        still = {_key(a) for a in after}
        for f in fixes:
            if f["status"] == "applied":
                f["status"] = "verified" if _key(f) not in still else "failed re-check"
        before_keys = {_key(b) for b in before}
        new = [a for a in after if _key(a) not in before_keys]
        # Safety net: a fix must never leave the page worse. If the re-check found new problems, rebuild the page
        # from the original with fewer fixes (first without structural role changes, then with none) and re-check.
        if new:
            structural = {"region", "landmark-one-main", "aria-required-parent", "aria-required-children"}
            applied_rules = sorted({f["rule"] for f in fixes if f["status"] in ("verified", "failed re-check")},
                                   key=lambda r: (r not in structural, r))  # riskiest first
            # Dynamic pages (tickers, rotating banners, random ids) differ on every load. A fresh, unfixed copy shows
            # which problems come from the page itself; those were never ours. Then re-test with every fix on a fresh
            # load, and only if a new problem remains, undo one kind, then all structural, then all.
            # ponytail: one probe load; content that changes on every single load can still slip through.
            _open(page, url)
            before_keys |= {_key(a) for a in _audit(page)}
            candidates = [set()] + [{r} for r in applied_rules] + [structural, None]
            first_pass = {id(f): f["status"] for f in fixes}
            for dropped in candidates:
                keep = [f for f in fixes if first_pass[id(f)] == "verified" and dropped is not None and f["rule"] not in dropped]
                _open(page, url)
                if keep:
                    page.add_script_tag(content=fix_script(url, keep, only_verified=False))
                after = _audit(page)
                still = {_key(a) for a in after}
                new = [a for a in after if _key(a) not in before_keys]
                for f in fixes:
                    if first_pass[id(f)] in ("verified", "failed re-check"):
                        if f in keep:
                            f["status"] = "verified" if _key(f) not in still else "failed re-check"
                            f.pop("why", None)
                        else:
                            f["status"] = "rolled back"
                            f["why"] = "undone automatically: with it applied, the re-check found a new problem"
                if not new:
                    break

        # A problem we didn't touch can still disappear: removing a broken role="tree" also repairs its list items.
        # The final re-check proves it, so say so instead of leaving it for a person.
        final = {_key(a) for a in after}
        for f in fixes:
            if f["status"] == "not fixed" and _key(f) not in final:
                f["status"], f["why"] = "resolved", "gone on the re-check after a related fix"

        result = {
            "url": url, "http_status": status, "blocked": blocked,
            "before": len(before), "after": len(after),
            "verified": sum(f["status"] == "verified" for f in fixes),
            "resolved": sum(f["status"] == "resolved" for f in fixes),
            "new_problems": new,
            "fixes": fixes,
            "reader_before": reader_before,
            "reader_after": page.locator("body").aria_snapshot(),
            "patched_html": page.content(),
            "shot_before": shot_before, "shot_after": _shot(page), "site_links": site_links,
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
    import argparse, json, sys
    ap = argparse.ArgumentParser(description="Check a page, fix what can be proven, re-check.")
    ap.add_argument("url")
    ap.add_argument("--no-ai", action="store_true", help="don't use the vision model for image and icon names")
    ap.add_argument("--json", action="store_true", help="print the full result as JSON")
    ap.add_argument("--max-after", type=int, default=None,
                    help="exit with code 1 if more than this many problems remain after fixing (for CI)")
    ap.add_argument("--script", metavar="FILE", help="also write the proven-fix script to FILE")
    a = ap.parse_args()
    r = run(a.url, describe=not a.no_ai)
    if a.script:
        pathlib.Path(a.script).write_text(r["fix_script"], encoding="utf-8")
    if a.json:
        print(json.dumps({k: v for k, v in r.items() if k not in ("patched_html", "shot_before", "shot_after")}, indent=2))
    else:
        print(json.dumps({k: r[k] for k in ("url", "before", "after", "verified", "blocked")}, indent=2))
        for f in r["fixes"]:
            print(f'{f["status"]:16} {f["rule"]:16} {f["target"][:40]:40} {f.get("change") or f.get("why", "")}')
        print("new problems introduced:", len(r["new_problems"]))
    if a.max_after is not None and r["after"] > a.max_after:
        print(f"FAIL: {r['after']} problems remain, more than the allowed {a.max_after}", file=sys.stderr)
        sys.exit(1)
