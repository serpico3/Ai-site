import base64
import json
import os
import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv

# OpenAI SDK v1
try:
    from openai import OpenAI
except Exception:
    OpenAI = None  # handled later


ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "articles"
ASSETS = ROOT / "assets" / "images"
DATA = ROOT / "data" / "posts.json"
TEMPLATE = ROOT / "templates" / "article.html"


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\-\s]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:80]


def ensure_dirs():
    ARTICLES.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ROOT / "data").mkdir(parents=True, exist_ok=True)


def load_posts():
    if DATA.exists():
        with open(DATA, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"version": 1, "posts": []}


def save_posts(data):
    DATA.parent.mkdir(parents=True, exist_ok=True)
    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def cosine(a: List[float], b: List[float]) -> float:
    import math
    da = math.sqrt(sum(x * x for x in a)) or 1.0
    db = math.sqrt(sum(x * x for x in b)) or 1.0
    return sum(x * y for x, y in zip(a, b)) / (da * db)


def load_template() -> str:
    with open(TEMPLATE, "r", encoding="utf-8") as f:
        return f.read()


def render_article_html(tpl: str, ctx: dict) -> str:
    def esc(s: str) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    html = tpl
    for k, v in ctx.items():
        if k in {"content_html"}:  # already HTML
            rep = str(v)
        else:
            rep = esc(v)
        html = html.replace("{{" + k + "}}", rep)
    return html


def estimate_read_minutes(text: str) -> int:
    words = len(re.findall(r"\w+", text))
    return max(3, round(words / 200))


PROMPT_TOPICS = (
    "AI e machine learning applicati a casi d'uso reali",
    "Sicurezza informatica e pratiche di hardening",
    "Sviluppo web moderno: performance e accessibilità",
    "Ingegneria del software: testing, CI/CD, DevOps",
    "Cloud e architetture serverless con esempi",
    "Data engineering e data pipelines",
    "Edge computing e IoT",
    "LLM applicati: agenti, RAG e tool use",
    "Open source highlight della settimana",
    "Carriera tech: strategie e best practice",
)


ARTICLE_SYSTEM = (
    "Sei un editor di un blog tech italiano. Scrivi articoli di 5 minuti, pratici, chiari e senza ripetizioni."
)


ARTICLE_USER_TEMPLATE = (
    "Scrivi un articolo originale in italiano su: '{topic}'.\n"
    "Requisiti:\n"
    "- Tempo di lettura ~5 minuti (800–1000 parole).\n"
    "- Struttura con titolo H1, sommario, 3–5 sezioni con H2, 1 box 'In pratica' con bullet.\n"
    "- Includi 3-5 tag rilevanti.\n"
    "- Evita contenuti ripetitivi rispetto a articoli precedenti su argomenti simili.\n"
    "Output JSON con campi: title, summary, sections (array di oggetti: heading, html), tags (array)."
)


IMAGE_PROMPT = (
    "Crea una illustrazione moderna in stile flat, isometrica leggera, colori scuri/accesi, su '{topic}'. Nessun testo."
)


def get_client():
    if os.getenv("DRY_RUN", "false").lower() == "true":
        class Dummy:
            pass
        return Dummy()
    if OpenAI is None:
        raise RuntimeError("SDK OpenAI non installato. Esegui: pip install -r requirements.txt")
    return OpenAI()


def embed(client, text: str) -> List[float]:
    if os.getenv("DRY_RUN", "false").lower() == "true":
        random.seed(hash(text) & 0xFFFF)
        return [random.random() for _ in range(256)]
    model = os.getenv("OPENAI_MODEL_EMBED", "text-embedding-3-small")
    resp = client.embeddings.create(model=model, input=text)
    return resp.data[0].embedding


def generate_article(client, topic: str) -> Tuple[dict, str]:
    if os.getenv("DRY_RUN", "false").lower() == "true":
        # minimal fake article
        sections = [
            {"heading": "Introduzione", "html": "<p>Testo introduttivo su %s.</p>" % topic},
            {"heading": "Approfondimento", "html": "<p>Dettagli e best practice.</p>"},
            {"heading": "In pratica", "html": "<ul><li>Punto 1</li><li>Punto 2</li></ul>"},
        ]
        article = {
            "title": f"{topic} – guida rapida",
            "summary": f"Una panoramica pratica su {topic}.",
            "sections": sections,
            "tags": ["tech", "daily"],
        }
        return article, "<p>Contenuto demo.</p>"

    model = os.getenv("OPENAI_MODEL_TEXT", "gpt-4o-mini")
    system = ARTICLE_SYSTEM
    user = ARTICLE_USER_TEMPLATE.format(topic=topic)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.9,
    )
    content = resp.choices[0].message.content
    data = json.loads(content)
    # Build HTML from sections
    parts = []
    for sec in data.get("sections", []):
        h = sec.get("heading", "").strip()
        parts.append(f"<h2>{h}</h2>\n{sec.get('html','')}")
    body_html = "\n".join(parts)
    return data, body_html


def generate_image(client, topic: str) -> bytes:
    if os.getenv("DRY_RUN", "false").lower() == "true":
        # 1x1 PNG placeholder
        return base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO3qv/0AAAAASUVORK5CYII="
        )
    model = os.getenv("OPENAI_MODEL_IMAGE", "gpt-image-1")
    prompt = IMAGE_PROMPT.format(topic=topic)
    img = client.images.generate(model=model, prompt=prompt, size="1024x576")
    b64 = img.data[0].b64_json
    return base64.b64decode(b64)


def pick_topic(existing: List[dict]) -> str:
    # Randomize a base topic with optional variant
    base = random.choice(PROMPT_TOPICS)
    suffix = random.choice([
        "casi d'uso pratici",
        "errori comuni e come evitarli",
        "strumenti essenziali",
        "trend del momento",
        "roadmap per iniziare",
        "pattern avanzati",
    ])
    return f"{base}: {suffix}"


def main():
    # Ensure .env is loaded from project root regardless of CWD
    load_dotenv(ROOT / ".env")
    ensure_dirs()
    posts = load_posts()

    client = get_client()

    # Generate candidate topic and article until non-duplicate
    try:
        max_attempts = int(os.getenv("MAX_ATTEMPTS", "4"))
    except ValueError:
        max_attempts = 4
    existing_embeddings = [p.get("embedding") for p in posts["posts"] if p.get("embedding")]

    for attempt in range(1, max_attempts + 1):
        topic = pick_topic(posts["posts"])
        article, body_html = generate_article(client, topic)
        title = article.get("title", topic)
        summary = article.get("summary", "")
        candidate_text = f"{title}\n\n{summary}"
        emb = embed(client, candidate_text)

        try:
            sim_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.88"))
        except ValueError:
            sim_threshold = 0.88

        too_similar = False
        for e in existing_embeddings:
            if not e:
                continue
            if cosine(emb, e) >= sim_threshold:
                too_similar = True
                break
        if not too_similar:
            break
        if attempt == max_attempts:
            # proceed anyway but mark topic as variant with timestamp
            title += f" ({datetime.now(timezone.utc).strftime('%Y-%m-%d')})"

    # Generate image
    img_bytes = generate_image(client, topic)

    # Persist files
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = slugify(title) or slugify(topic) or f"post-{date_str}"

    img_name = f"{date_str}-{slug}.png"
    img_path = ASSETS / img_name
    with open(img_path, "wb") as f:
        f.write(img_bytes)

    # Build article HTML
    tpl = load_template()
    read_minutes = estimate_read_minutes(" ".join(
        [article.get("summary", "")] + [re.sub(r"<[^>]+>", " ", s.get("html", "")) for s in article.get("sections", [])]
    ))
    content_html = body_html
    ctx = {
        "title": title,
        "summary": summary,
        "date": date_str,
        "read_minutes": read_minutes,
        "tags": ", ".join(article.get("tags", [])),
        "image": f"assets/images/{img_name}",
        "content_html": content_html,
    }

    art_name = f"{date_str}-{slug}.html"
    art_path = ARTICLES / art_name
    html = render_article_html(tpl, ctx)
    with open(art_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Update dataset
    post_record = {
        "title": title,
        "summary": summary,
        "date": date_str,
        "read_minutes": read_minutes,
        "tags": article.get("tags", []),
        "image": f"assets/images/{img_name}",
        "path": f"articles/{art_name}",
        "embedding": emb,
        "topic": topic,
    }
    posts["posts"].append(post_record)
    save_posts(posts)

    # Optional auto-commit
    if os.getenv("GIT_AUTO_COMMIT", "false").lower() == "true":
        os.system("git add -A")
        os.system(f"git commit -m \"chore: publish article {art_name}\"")
        os.system("git push")

    print(json.dumps({"created": post_record}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
