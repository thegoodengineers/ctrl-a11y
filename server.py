"""Web app: paste a URL, get the audit, the verified fixes, the screen-reader views and the patched page."""
import os
import pathlib
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import a11y

HERE = pathlib.Path(__file__).parent
app = FastAPI(title="Ctrl+A11y")
app.mount("/demo", StaticFiles(directory=HERE / "demo"), name="demo")
patched = {}  # ponytail: in-memory store, lost on restart; fine for a demo, use a disk/S3 store if hosted


class Job(BaseModel):
    url: str


@app.get("/")
def index():
    return FileResponse(HERE / "web/index.html")


@app.get("/api/status")
def status():
    return {"ai": bool(os.environ.get("CTRL_A11Y_ANTHROPIC_API_KEY") and os.environ.get("CTRL_A11Y_MODEL"))}


@app.post("/api/run")
def run(job: Job):  # sync def: FastAPI runs it in a thread, so sync Playwright is fine
    if not job.url.startswith(("http://", "https://")):
        raise HTTPException(400, "Paste a full URL starting with http:// or https://")
    try:
        r = a11y.run(job.url)
    except Exception as e:
        raise HTTPException(502, f"Could not load or audit that page: {str(e).splitlines()[0][:200]}")
    rid = uuid.uuid4().hex[:8]
    patched[rid] = r.pop("patched_html")
    r["patched_id"] = rid
    return r


@app.get("/api/patched/{rid}")
def download(rid: str):
    if rid not in patched:
        raise HTTPException(404, "Run the audit again; patched pages are kept only while the server runs.")
    return HTMLResponse(patched[rid], headers={"Content-Disposition": f"attachment; filename=patched-{rid}.html"})
