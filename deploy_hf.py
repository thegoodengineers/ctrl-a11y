"""Publish Ctrl+A11y as a free public demo on Hugging Face Spaces (Docker).

    python -m pip install huggingface_hub
    set HF_TOKEN to a write token from https://huggingface.co/settings/tokens (your own environment only)
    python deploy_hf.py <hf-username-or-org>/ctrl-a11y

The Space builds the Dockerfile; the first build takes a few minutes. The demo is then live at
https://<user>-ctrl-a11y.hf.space . Re-run the script to update it.
"""
import os
import sys

from huggingface_hub import HfApi

SPACE_CARD = """---
title: Ctrl+A11y
emoji: ♿
colorFrom: gray
colorTo: green
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Paste a URL. Get it fixed, with every fix proven.
---
Ctrl+A11y finds accessibility barriers on any page, fixes what it can, and proves every fix by running the
same checker again. Code and results: https://github.com/thegoodengineers/ctrl-a11y
"""

if __name__ == "__main__":
    if len(sys.argv) != 2 or "/" not in sys.argv[1] or not os.environ.get("HF_TOKEN"):
        sys.exit(__doc__)
    space = sys.argv[1]
    api = HfApi(token=os.environ["HF_TOKEN"])
    api.create_repo(space, repo_type="space", space_sdk="docker", exist_ok=True)
    api.upload_folder(repo_id=space, repo_type="space", folder_path=os.path.dirname(os.path.abspath(__file__)),
                      ignore_patterns=["node_modules/*", "__pycache__/*", ".pytest_cache/*", ".git/*", ".github/*",
                                       "video/*", "results/*.png", ".env", "README.md"],
                      commit_message="Update Ctrl+A11y")
    api.upload_file(path_or_fileobj=SPACE_CARD.encode(), path_in_repo="README.md", repo_id=space, repo_type="space",
                    commit_message="Space card")
    user, name = space.split("/")
    print(f"Building now. Live in a few minutes at https://{user}-{name}.hf.space".lower())
