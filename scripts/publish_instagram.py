import os
import re
import json
from pathlib import Path
from datetime import datetime
import requests

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "posts.json"


def pick_caption(post: dict) -> str:
    title = post.get("title", "").strip()
    summary = post.get("summary", "").strip()
    tags = post.get("tags", [])
    base = f"{title}\n\n{summary}"
    if tags:
        base += "\n\n" + " ".join("#" + re.sub(r"\W+", "", t.lower()) for t in tags[:5])
    base += "\n\n#tech #coding #ai #dev"
    return base[:2200]


def main():
    load_dotenv(ROOT / ".env")
    with open(DATA, encoding="utf-8") as f:
        posts = json.load(f)["posts"]
    if not posts:
        print("No posts to publish")
        return
    post = sorted(posts, key=lambda p: p.get("date", ""))[-1]
    image_rel = post["image"]
    caption = pick_caption(post)

    # Build a public raw URL to the image (repo must be public)
    repo = os.getenv("GITHUB_REPOSITORY")  # owner/repo
    branch = os.getenv("GITHUB_REF_NAME", "main")
    if repo:
        raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{image_rel}"
    else:
        raw_url = None

    out = {"image_path": str(ROOT / image_rel), "image_url": raw_url, "caption": caption}

    ig_token = os.getenv("IG_ACCESS_TOKEN")
    ig_user = os.getenv("IG_USER_ID")

    if not ig_token or not ig_user or not raw_url:
        out["note"] = "Missing IG secrets or repo context; prepared payload only."
        print(json.dumps(out, ensure_ascii=False))
        return

    # 1) Create media container
    create_url = f"https://graph.facebook.com/v19.0/{ig_user}/media"
    r = requests.post(create_url, data={
        "image_url": raw_url,
        "caption": caption,
        "access_token": ig_token,
    }, timeout=60)
    r.raise_for_status()
    creation_id = r.json().get("id")
    if not creation_id:
        raise RuntimeError("Instagram create container failed")

    # 2) Publish media
    pub_url = f"https://graph.facebook.com/v19.0/{ig_user}/media_publish"
    r2 = requests.post(pub_url, data={
        "creation_id": creation_id,
        "access_token": ig_token,
    }, timeout=60)
    r2.raise_for_status()
    media_id = r2.json().get("id")

    # 3) Optional: fetch permalink
    permalink = None
    if media_id:
        r3 = requests.get(f"https://graph.facebook.com/v19.0/{media_id}", params={
            "fields": "permalink",
            "access_token": ig_token,
        }, timeout=60)
        if r3.ok:
            permalink = r3.json().get("permalink")

    out.update({"creation_id": creation_id, "media_id": media_id, "permalink": permalink})
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
