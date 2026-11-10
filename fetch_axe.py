"""Fetch axe-core exactly as package-lock.json pins it (same URL, checksum verified) without installing Node.js.
Used by the Dockerfile; locally, `npm install` does the same job."""
import base64
import hashlib
import io
import json
import pathlib
import tarfile
import urllib.request

ROOT = pathlib.Path(__file__).parent
lock = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))["packages"]["node_modules/axe-core"]
data = urllib.request.urlopen(lock["resolved"], timeout=60).read()
algo, expected = lock["integrity"].split("-", 1)
if base64.b64encode(hashlib.new(algo, data).digest()).decode() != expected:
    raise SystemExit("axe-core download does not match package-lock.json; refusing to use it")
out = ROOT / "node_modules" / "axe-core"
out.mkdir(parents=True, exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(data)) as tar:
    (out / "axe.min.js").write_bytes(tar.extractfile("package/axe.min.js").read())
print("axe-core", lock["version"], "verified")
