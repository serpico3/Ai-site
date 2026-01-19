#!/usr/bin/env python3
"""
Instagram post automation: generate image + caption (prepare) and publish
to Instagram (publish) via Instagram Graph API.

Two-step flow avoids race with GitHub Pages:
- prepare: generate image under docs/instagram + caption, save metadata
- publish: after commit/push, publish using raw.githubusercontent.com URL
"""

import os
import sys
import time
import json
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import requests
from PIL import Image, ImageDraw, ImageFont


def generate_image_with_text(title: str, subtitle: str, output_path: str) -> str:
    """Create a 1080x1080 image suitable for Instagram posts."""
    print(f"🖼️ Creating image: {output_path}")

    img = Image.new('RGB', (1080, 1080), color=(5, 7, 10))
    draw = ImageDraw.Draw(img)

    # Vertical gradient
    for y in range(1080):
        r = int(5 + (66 - 5) * (y / 1080))
        g = int(7 + (179 - 7) * (y / 1080))
        b = int(10 + (255 - 10) * (y / 1080))
        draw.line([(0, y), (1080, y)], fill=(r, g, b))

    # Fonts
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        subtitle_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 40)
        print("✅ System fonts loaded")
    except Exception as e:
        print(f"⚠️ System fonts not found: {e}, using default")
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()

    # Title wrap
    wrapped_title = textwrap.fill(title, width=20)

    # Centered text
    y_offset = 300
    for line in wrapped_title.split('\n'):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        line_width = bbox[2] - bbox[0]
        x = (1080 - line_width) // 2
        draw.text((x, y_offset), line, fill=(255, 255, 255), font=title_font)
        y_offset += 80

    y_offset += 60
    bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    line_width = bbox[2] - bbox[0]
    x = (1080 - line_width) // 2
    draw.text((x, y_offset), subtitle, fill=(66, 179, 255), font=subtitle_font)

    img.save(output_path)
    print(f"✅ Image saved: {output_path}")
    return output_path


def generate_caption(topic: str) -> str:
    """Generate Instagram caption using Groq API."""
    from groq import Groq

    print("📝 Generating caption...")
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("Missing GROQ_API_KEY")
    print(f"✅ GROQ_API_KEY: {api_key[:10]}...")

    client = Groq(api_key=api_key)

    prompt = f"""Sei Diego Serpelloni, 22 anni, tech enthusiast.

Genera una caption accattivante per Instagram post su: {topic}

REQUISITI:
- Lunghezza: 150-250 caratteri
- Tono: Giovane, entusiasta, informativo
- Linguaggio: Italiano
- Includi 3-4 hashtag rilevanti (es. #DevOps #Tech #Networking)
- NO emoji
- Chiudi con una call-to-action (es. "Cosa ne pensi?")

Scrivi SOLO la caption, niente altro."""

    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        max_tokens=300,
        temperature=0.7,
    )

    caption = response.choices[0].message.content.strip()
    print(f"✅ Caption generated ({len(caption)} chars)")
    print(f"   Preview: {caption[:80]}...")
    return caption


def save_post_metadata(caption: str, image_filename: str) -> Path:
    """Save caption and filename under temp/ for later publish step."""
    repo_root = Path(__file__).parent.parent
    temp_dir = repo_root / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    (temp_dir / "instagram_caption.txt").write_text(caption, encoding="utf-8")
    meta = {"caption": caption, "image_filename": image_filename}
    meta_path = temp_dir / "instagram_post.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 Saved metadata: {meta_path}")
    return meta_path


def load_post_metadata() -> Optional[Tuple[str, str]]:
    repo_root = Path(__file__).parent.parent
    meta_path = repo_root / "temp" / "instagram_post.json"
    if not meta_path.exists():
        return None
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    return data.get("caption"), data.get("image_filename")


def publish_to_instagram(image_url: str, caption: str) -> bool:
    """Publish image + caption via Instagram Graph API using a public URL.

    Uses graph.facebook.com endpoints as per API docs.
    """
    print("\n=== 📤 Publishing to Instagram ===")

    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    business_account_id = os.environ.get("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    if not access_token or not business_account_id:
        print("❌ Missing INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_BUSINESS_ACCOUNT_ID")
        return False

    print(f"🔐 TOKEN: {access_token[:10]}...")
    print(f"👤 IG_USER_ID: {business_account_id}")
    print(f"🖼️ Image URL: {image_url}")

    try:
        # Step 1: Create media container
        print("🧰 Step 1: Creating media container...")
        container_url = f"https://graph.facebook.com/v18.0/{business_account_id}/media"
        payload = {
            'image_url': image_url,
            'caption': caption,
            'access_token': access_token,
        }
        response = requests.post(container_url, data=payload, timeout=30)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:300]}")
        if response.status_code != 200:
            print(f"❌ Error creating media container: {response.status_code}")
            print(f"   Full response: {response.text}")
            return False
        result = response.json()
        if 'error' in result or 'id' not in result:
            print(f"❌ API Error: {result}")
            return False
        media_id = result['id']
        print(f"✅ Media container created: {media_id}")

        # Step 2: Publish media
        print("🚀 Step 2: Publishing media...")
        publish_url = f"https://graph.facebook.com/v18.0/{business_account_id}/media_publish"
        publish_data = {'creation_id': media_id, 'access_token': access_token}
        publish_response = requests.post(publish_url, data=publish_data, timeout=30)
        print(f"   Status: {publish_response.status_code}")
        print(f"   Response: {publish_response.text[:300]}")
        if publish_response.status_code != 200:
            print(f"❌ Error publishing: {publish_response.status_code}")
            print(f"   Response: {publish_response.text}")
            return False
        publish_result = publish_response.json()
        if 'id' not in publish_result:
            print(f"❌ No post ID in response: {publish_result}")
            return False
        post_id = publish_result['id']
        print(f"🎉 Post published! IG media id: {post_id}")

        # Step 3: Fetch permalink for convenience
        try:
            perm_url = f"https://graph.facebook.com/v18.0/{post_id}?fields=permalink&access_token={access_token}"
            pr = requests.get(perm_url, timeout=15)
            if pr.status_code == 200:
                link = pr.json().get('permalink')
                if link:
                    print(f"🔗 Permalink: {link}")
        except Exception:
            pass

        return True

    except requests.exceptions.Timeout:
        print("❌ Request timeout (Instagram API took too long)")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ Connection error (network issue)")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def build_raw_github_url(repo: str, image_filename: str) -> str:
    return f"https://raw.githubusercontent.com/{repo}/main/docs/instagram/{image_filename}"


def wait_for_url(url: str, timeout_sec: int = 90) -> bool:
    """Poll HEAD until status 200 or timeout."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            r = requests.head(url, timeout=5)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(3)
    return False


def main():
    """CLI entry.
    Modes:
    - prepare (default): generate image+caption and save metadata (no publish)
    - publish: publish using saved metadata and raw.githubusercontent.com URL
    """
    print("=" * 60)
    print("📷 Instagram Post Generator")
    print("=" * 60)

    mode = (sys.argv[1] if len(sys.argv) > 1 else "prepare").lower()
    print(f"Mode: {mode}")

    try:
        repo_root = Path(__file__).parent.parent
        instagram_dir = repo_root / "docs" / "instagram"
        instagram_dir.mkdir(parents=True, exist_ok=True)

        if mode == "prepare":
            now = datetime.now()
            topic = "Ultimi trends in DevOps e Infrastructure as Code"
            caption = generate_caption(topic)

            image_filename = f"instagram_post_{now.strftime('%Y%m%d')}.png"
            image_path = instagram_dir / image_filename
            generate_image_with_text(
                title="Tech Blog",
                subtitle="Nuovo articolo",
                output_path=str(image_path)
            )
            save_post_metadata(caption, image_filename)
            print("\n✅ Prepared IG assets (no publish in this step)")
            print(f"   Image: {image_path}")
            print(f"   Caption: temp/instagram_caption.txt")

        elif mode == "publish":
            loaded = load_post_metadata()
            if not loaded:
                raise RuntimeError("instagram_post.json not found; run prepare first.")
            caption, image_filename = loaded

            repo = os.environ.get("GITHUB_REPOSITORY", "serpico3/Ai-site")
            image_url = build_raw_github_url(repo, image_filename)
            print(f"Will publish with image URL: {image_url}")
            if not wait_for_url(image_url, timeout_sec=90):
                print("⚠️ Raw image URL not yet available; attempting publish anyway.")

            success = publish_to_instagram(image_url, caption)
            if success:
                print("\n✅ Instagram post published successfully!")
            else:
                print("\n❌ Instagram publishing failed")
                print(f"   Tried URL: {image_url}")

        else:
            raise ValueError("Unknown mode. Use 'prepare' or 'publish'.")

        print("\n" + "=" * 60)
        print("Done.")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ FATAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

