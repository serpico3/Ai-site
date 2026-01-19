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
import requests


ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content" / "posts"
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
    "Output SOLO JSON valido con campi: title, excerpt, tags, content_markdown.\n"
    "Il JSON deve essere valido: nessun markdown, nessun backtick, nessuna riga extra.\n"
    "Nel campo content_markdown usa \\n per i ritorni a capo (non inserire newline raw dentro le stringhe).\n"
    "content_markdown NON deve includere un titolo H1 (il titolo e separato).\n"
    "tags: 4-7 tag, minuscoli, con trattini, evita tag generici come tech o news.\n"
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


def is_quota_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return "insufficient_quota" in text or "rate limit" in text or "429" in text


def yaml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def extract_json(text: str) -> dict:
    candidate = extract_json_block(text)
    try:
        return json.loads(candidate)
    except Exception:
        repaired = repair_json_text(candidate)
        return json.loads(repaired)


def extract_json_block(text: str) -> str:
    if "```" in text:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S | re.I)
        if match:
            return match.group(1).strip()
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("Risposta senza JSON valido")
    return match.group(0).strip()


def repair_json_text(text: str) -> str:
    cleaned = (
        text.replace("“", '"')
        .replace("”", '"')
        .replace("’", "'")
        .replace("‘", "'")
    )
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)

    out = []
    in_string = False
    escape = False
    for ch in cleaned:
        if in_string:
            if escape:
                out.append(ch)
                escape = False
                continue
            if ch == "\\":
                out.append(ch)
                escape = True
                continue
            if ch == '"':
                in_string = False
                out.append(ch)
                continue
            if ch == "\n":
                out.append("\\n")
                continue
            if ch == "\r":
                continue
            if ch == "\t":
                out.append("\\t")
                continue
        else:
            if ch == '"':
                in_string = True
                out.append(ch)
                continue
        out.append(ch)
    return "".join(out)


def default_cover_image() -> str:
    preferred = os.getenv("DEFAULT_COVER_IMAGE") or "assets/images/pcb-bg.png"
    if (ROOT / preferred).exists():
        return preferred
    return "assets/images/chip.svg"


def generate_with_perplexity(
    model: str,
    system_prompt: str,
    user_prompt: str,
    fallback_models: List[str],
    max_tokens: int,
) -> dict:
    key = os.getenv("PERPLEXITY_API_KEY")
    if not key:
        raise RuntimeError("PERPLEXITY_API_KEY mancante. Configura .env o secrets.")

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    def is_model_error(message: str) -> bool:
        msg = message.lower()
        return "model" in msg and ("invalid" in msg or "not found" in msg or "does not exist" in msg)

    models = [model] + [m for m in fallback_models if m and m != model]
    last_error = None

    for candidate in models:
        payload = {
            "model": candidate,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": max_tokens,
        }
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers=headers,
            json=payload,
            timeout=90,
        )
        if resp.status_code == 429:
            raise RuntimeError("rate limit")

        if resp.ok:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return extract_json(content)

        try:
            data = resp.json()
            error_message = data.get("error", {}).get("message", "")
        except Exception:
            error_message = resp.text.strip()

        last_error = f"{resp.status_code}: {error_message or resp.text.strip()}"
        if resp.status_code == 400 and is_model_error(error_message):
            continue
        raise RuntimeError(f"Perplexity error: {last_error}")

    raise RuntimeError(f"Perplexity error: {last_error}")


def main():
    load_dotenv(ROOT / ".env")
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    topics = load_topics()
    log = load_log()
    if not topics:
        raise RuntimeError("Lista topics vuota. Aggiorna data/topics.json")
    topic = pick_topic(topics, log.get("entries", []))

    dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
    text_model = os.getenv("PERPLEXITY_TEXT_MODEL") or "sonar-pro"
    fallback_models = [
        m.strip()
        for m in (os.getenv("PERPLEXITY_FALLBACK_MODELS") or "sonar").split(",")
        if m.strip()
    ]
    try:
        max_tokens = int(os.getenv("PERPLEXITY_MAX_TOKENS") or "1800")
    except ValueError:
        max_tokens = 1800

    if dry_run:
        article = {
            "title": f"{topic} - guida pratica",
            "excerpt": f"Guida rapida per {topic}.",
            "tags": ["linux", "sysadmin", "backup", "hardening"],
            "content_markdown": "## Introduzione\nContenuto di test.",
        }
    else:
        try:
            article = generate_with_perplexity(
                text_model,
                SYSTEM_PROMPT,
                USER_PROMPT.format(topic=topic),
                fallback_models,
                max_tokens,
            )
        except Exception as exc:
            if is_quota_error(exc):
                print("Quota Perplexity esaurita. Nessun articolo pubblicato.")
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

    cover_image = default_cover_image()

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
            f'cover_image: "{cover_image}"',
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

    print(json.dumps({"created": content_file.name, "image": cover_image}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
