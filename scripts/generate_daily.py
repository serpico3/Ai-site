import base64
import io
import json
import os
import random
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content" / "posts"
IMAGES_DIR = ROOT / "assets" / "images"
TOPICS_PATH = ROOT / "data" / "topics.json"
LOG_PATH = ROOT / "data" / "generated_log.json"

SYSTEM_PROMPT = (
    "Sei Diego, sistemista junior e docente di Python in una scuola. "
    "Scrivi articoli tecnici pratici, stile how-to, con comandi reali e checklist. "
    "Tono semplice, tecnico, niente marketing e niente clickbait. "
    "In cybersecurity concentrati su hardening, difesa e best practice."
)

USER_PROMPT = (
    "Topic: {topic}\n"
    "Scrivi un articolo in italiano da 800 a 1400 parole.\n"
    "Struttura obbligatoria (con titoli H2):\n"
    "1) Introduzione (2-4 righe)\n"
    "2) Scenario reale\n"
    "3) Procedura step-by-step\n"
    "4) Comandi (includi almeno un blocco bash; powershell solo se serve)\n"
    "5) Errori comuni e fix\n"
    "6) Hardening / Sicurezza\n"
    "7) Checklist\n"
    "8) Mini glossario (max 5 voci)\n"
    "9) Conclusione con recap\n"
    "Aggiungi esempi concreti (permessi Linux, backup, firewall, VLAN, logging, fail2ban, update policy).\n"
    "Output SOLO JSON con campi: title, excerpt, tags, content_markdown.\n"
    "content_markdown NON deve includere un titolo H1 (il titolo e separato).\n"
    "tags: 4-7 tag, minuscoli, con trattini, evita tag generici come tech o news.\n"
)

IMAGE_PROMPT = (
    "Realistic PCB background, dark green and black palette, "
    "thin traces, pads, vias, soft blur, professional and clean. "
    "No text, no logos, no people."
)

BAD_TAGS = {"tech", "news", "blog", "articolo", "ai", "software", "informatica"}
FALLBACK_TAGS = [
    "linux",
    "sysadmin",
    "hardening",
    "backup",
    "networking",
    "storage",
    "monitoring",
    "automazione",
    "sicurezza",
    "python",
]


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\\s-]", "", text)
    text = re.sub(r"\\s+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def load_topics() -> List[str]:
    if TOPICS_PATH.exists():
        return json.loads(TOPICS_PATH.read_text(encoding="utf-8"))
    return [
        "Gestione permessi e gruppi su Linux",
        "Hardening SSH su server Debian",
        "Backup e restore per cartelle studenti",
    ]


def load_log() -> dict:
    if LOG_PATH.exists():
        return json.loads(LOG_PATH.read_text(encoding="utf-8"))
    return {"version": 1, "entries": []}


def save_log(log: dict):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")


def pick_topic(topics: List[str], log_entries: List[dict]) -> str:
    recent = [e.get("topic") for e in log_entries[-7:]]
    available = [t for t in topics if t not in recent]
    if not available:
        available = topics
    return random.choice(available)


def normalize_tags(tags: List[str]) -> List[str]:
    seen = set()
    cleaned = []
    for tag in tags:
        norm = slugify(tag)
        if not norm or norm in BAD_TAGS or len(norm) < 3:
            continue
        if norm not in seen:
            cleaned.append(norm)
            seen.add(norm)
    for fallback in FALLBACK_TAGS:
        if len(cleaned) >= 4:
            break
        if fallback not in seen:
            cleaned.append(fallback)
            seen.add(fallback)
    return cleaned[:7]


def ensure_unique_slug(base_slug: str) -> str:
    slug = base_slug or "articolo"
    candidate = slug
    counter = 2
    def exists(name: str) -> bool:
        return any(CONTENT_DIR.glob(f"*-{name}.md"))

    while exists(candidate):
        candidate = f"{slug}-{counter}"
        counter += 1
    return candidate


def create_placeholder_image() -> bytes:
    img = Image.new("RGB", (1024, 576), color=(10, 20, 15))
    buf = io.BytesIO()
    img.save(buf, format="WEBP", quality=80)
    return buf.getvalue()


def is_quota_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "insufficient_quota" in text or "rate limit" in text or "429" in text


def yaml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def main():
    load_dotenv(ROOT / ".env")
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    topics = load_topics()
    log = load_log()
    if not topics:
        raise RuntimeError("Lista topics vuota. Aggiorna data/topics.json")
    topic = pick_topic(topics, log.get("entries", []))

    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    text_model = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
    image_model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")

    if dry_run:
        article = {
            "title": f"{topic} - guida pratica",
            "excerpt": f"Guida rapida per {topic}.",
            "tags": ["linux", "sysadmin", "backup", "hardening"],
            "content_markdown": "## Introduzione\nContenuto di test.",
        }
        image_bytes = create_placeholder_image()
    else:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY mancante. Configura .env o secrets.")
        client = OpenAI()
        try:
            response = client.chat.completions.create(
                model=text_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": USER_PROMPT.format(topic=topic)},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            article = json.loads(response.choices[0].message.content)
        except Exception as exc:
            if is_quota_error(exc):
                print("Quota OpenAI esaurita. Nessun articolo pubblicato.")
                sys.exit(0)
            raise

        try:
            image_response = client.images.generate(
                model=image_model,
                prompt=IMAGE_PROMPT,
                size="1024x576",
                response_format="b64_json",
            )
            image_b64 = getattr(image_response.data[0], "b64_json", None)
            if not image_b64:
                raise RuntimeError("Risposta immagini senza b64_json")
            image_bytes = base64.b64decode(image_b64)
        except Exception as exc:
            if is_quota_error(exc):
                print("Quota immagini OpenAI esaurita. Nessuna pubblicazione.")
                sys.exit(0)
            raise

    title = str(article.get("title", topic)).strip()
    excerpt = str(article.get("excerpt", "")).strip()
    content_md = str(article.get("content_markdown", "")).strip()
    tags = normalize_tags(article.get("tags", []))

    if not content_md:
        content_md = "## Introduzione\nContenuto non disponibile.\n"

    if len(excerpt) > 180:
        excerpt = excerpt[:177].rstrip() + "..."

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = ensure_unique_slug(slugify(title))

    image_name = f"{date_str}-{slug}.webp"
    image_path = IMAGES_DIR / image_name

    if not dry_run:
        img = Image.open(io.BytesIO(image_bytes))
        img = img.convert("RGB")
        img.save(image_path, format="WEBP", quality=82, method=6)
    else:
        image_path.write_bytes(image_bytes)

    content_file = CONTENT_DIR / f"{date_str}-{slug}.md"
    safe_title = yaml_escape(title)
    safe_excerpt = yaml_escape(excerpt)
    safe_slug = yaml_escape(slug)
    frontmatter = [
        "---",
        f'title: "{safe_title}"',
        f'date: "{date_str}"',
        "tags:",
    ]
    for tag in tags:
        frontmatter.append(f"  - {tag}")
    frontmatter.extend(
        [
            f'slug: "{safe_slug}"',
            f'excerpt: "{safe_excerpt}"',
            f'cover_image: "assets/images/{image_name}"',
            'author: "Diego"',
            "---",
            "",
        ]
    )
    content_file.write_text("\n".join(frontmatter) + content_md + "\n", encoding="utf-8")

    log["entries"].append({"topic": topic, "slug": slug, "date": date_str})
    save_log(log)

    if os.getenv("RUN_BUILD", "true").lower() == "true":
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build_site.py")], check=True)

    print(json.dumps({"created": content_file.name, "image": image_name}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
