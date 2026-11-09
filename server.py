"""Web app: paste a URL, get the audit, the verified fixes, the screen-reader views and the patched page.
Also serves the live fix script for the "Fix this page" bookmarklet."""
import ipaddress
import os
import pathlib
import socket
import time
import uuid
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import a11y

HERE = pathlib.Path(__file__).parent
app = FastAPI(title="Ctrl+A11y")
app.mount("/demo", StaticFiles(directory=HERE / "demo"), name="demo")
patched = {}  # ponytail: in-memory store, lost on restart; fine for a demo, use a disk/S3 store if hosted
run_cache = {}  # url -> (time, full result) so a page checked in the last 10 minutes returns at once
live_cache = {}  # url -> (time, script); ponytail: in-memory, per process; use Redis if hosted with several workers
LIVE_TTL = 600


class Job(BaseModel):
    url: str


def check_url(url: str, request: Request) -> str:
    """Only public http(s) pages. Private and internal addresses are refused so the server can't be used to
    probe the network it runs on; the server's own host is allowed so the demo pages work."""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise HTTPException(400, "Paste a full address starting with http:// or https://")
    if parts.hostname == request.url.hostname:
        return url
    try:
        addrs = {info[4][0] for info in socket.getaddrinfo(parts.hostname, parts.port or 443)}
    except socket.gaierror:
        raise HTTPException(400, f"Can't find the site {parts.hostname}. Check the address and try again.")
    for a in addrs:
        ip = ipaddress.ip_address(a.split("%")[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise HTTPException(400, "That address points to a private or internal network, which this tool doesn't check.")
    return url


@app.get("/")
def index():
    return FileResponse(HERE / "web/index.html")


@app.get("/api/status")
def status():
    return {"ai": bool(os.environ.get("CTRL_A11Y_VISION_API_KEY") and os.environ.get("CTRL_A11Y_MODEL"))}


@app.post("/api/run")
def run(job: Job, request: Request):  # sync def: FastAPI runs it in a thread, so sync Playwright is fine
    url = check_url(job.url, request)
    hit = run_cache.get(url)
    if hit and time.time() - hit[0] < LIVE_TTL:
        return {**hit[1], "cached_seconds_ago": int(time.time() - hit[0])}
    try:
        r = a11y.run(url)
    except Exception as e:
        raise HTTPException(502, f"Could not load or audit that page: {str(e).splitlines()[0][:200]}")
    rid = uuid.uuid4().hex[:8]
    patched[rid] = r.pop("patched_html")
    r["patched_id"] = rid
    live_cache[url] = (time.time(), r["fix_script"])
    run_cache[url] = (time.time(), r)
    return r


@app.get("/api/patched/{rid}")
def download(rid: str):
    if rid not in patched:
        raise HTTPException(404, "Run the audit again; patched pages are kept only while the server runs.")
    return HTMLResponse(patched[rid], headers={"Content-Disposition": f"attachment; filename=patched-{rid}.html"})


ANNOUNCE = """
;(function () {  /* Tell screen-reader users the fixes are in, then tidy up. */
  var live = document.createElement("div");
  live.setAttribute("role", "status");
  live.style.cssText = "position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)";
  document.body.appendChild(live);
  setTimeout(function () { live.textContent = "Ctrl+A11y applied " + COUNT + " proven accessibility fixes to this page."; }, 300);
  setTimeout(function () { live.remove(); }, 8000);
})();
"""


def _with_announcement(script: str) -> str:
    import re
    m = re.search(r": (\d+) fixes, each proven", script)
    return script + ANNOUNCE.replace("COUNT", m.group(1) if m else "0")


@app.get("/api/fix.js")
def live_fix(url: str, request: Request, announce: int = 0):
    """The bookmarklet loads this from any page: it returns that page's proven fixes as a script.
    With announce=1 it also tells screen-reader users how many fixes were applied."""
    js = {"Content-Type": "text/javascript; charset=utf-8", "Access-Control-Allow-Origin": "*", "Cache-Control": "no-store"}
    finish = _with_announcement if announce else (lambda s: s)
    try:
        url = check_url(url, request)
    except HTTPException as e:
        return Response(f"console.warn({e.detail!r});", headers=js)
    hit = live_cache.get(url)
    if hit and time.time() - hit[0] < LIVE_TTL:
        return Response(finish(hit[1]), headers=js)
    try:
        script = a11y.run(url)["fix_script"]
    except Exception as e:
        return Response(f"console.warn('Ctrl+A11y could not check this page: ' + {str(e).splitlines()[0][:120]!r});", headers=js)
    live_cache[url] = (time.time(), script)
    return Response(finish(script), headers=js)
