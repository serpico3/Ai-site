import base64
import json
import os
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

import requests
from dotenv import load_dotenv

try:
    from groq import Groq
except Exception:
    Groq = None


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


def get_groq_client():
    if os.getenv("DRY_RUN", "false").lower() == "true":
        class Dummy:
            def __init__(self):
                self.chat = self
                self.completions = self

            def create(self, **kwargs):
                class Resp:
                    class C:
                        class M:
                            content = json.dumps({
                                "title": "Articolo demo",
                                "summary": "Sommario demo.",
                                "sections": [
                                    {"heading": "Introduzione", "html": "<p>Testo introduttivo.</p>"},
                                    {"heading": "In pratica", "html": "<ul><li>Punto</li></ul>"},
                                ],
                                "tags": ["tech", "daily"],
                            })
                        message = M()
                    choices = [C()]
                return Resp()

        return Dummy()
    if Groq is None:
        raise RuntimeError("SDK Groq non installato. Esegui: pip install -r requirements.txt")
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        return Groq(api_key=api_key)
    return Groq()


def too_similar(candidate_text: str, posts: List[dict], threshold: float) -> bool:
    texts = []
    for p in posts:
        t = f"{p.get('title','')}\n\n{p.get('summary','')}".strip()
        if t:
            texts.append(t)
    if not texts:
        return False
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
        X = vec.fit_transform(texts + [candidate_text])
        sims = cosine_similarity(X[-1], X[:-1]).ravel()
        return float(sims.max()) >= threshold
    except Exception:
        def tok(s: str):
            return set(re.findall(r"\w+", s.lower()))

        c = tok(candidate_text)
        for t in texts:
            u = tok(t)
            m = len(c & u) / (len(c | u) or 1)
            if m >= max(0.3, threshold - 0.4):
                return True
        return False


def generate_article(groq_client, topic: str) -> Tuple[dict, str]:
    if os.getenv("DRY_RUN", "false").lower() == "true":
        sections = [
            {"heading": "Introduzione", "html": f"<p>Testo introduttivo su {topic}.</p>"},
            {"heading": "Approfondimento", "html": "<p>Dettagli e best practice.</p>"},
            {"heading": "In pratica", "html": "<ul><li>Punto 1</li><li>Punto 2</li></ul>"},
        ]
        article = {
            "title": f"{topic} – guida rapida",
            "summary": f"Una panoramica pratica su {topic}.",
            "sections": sections,
            "tags": ["tech", "daily"],
        }
        return article, "\n".join([f"<h2>{s['heading']}</h2>\n{s['html']}" for s in sections])

    model = os.getenv("GROQ_MODEL_TEXT", "llama-3.1-70b-versatile")
    system = ARTICLE_SYSTEM
    user = ARTICLE_USER_TEMPLATE.format(topic=topic)
    resp = groq_client.chat.completions.create(
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
    parts = []
    for sec in data.get("sections", []):
        h = sec.get("heading", "").strip()
        parts.append(f"<h2>{h}</h2>\n{sec.get('html','')}")
    body_html = "\n".join(parts)
    return data, body_html


def generate_image(topic: str) -> bytes:
    if os.getenv("DRY_RUN", "false").lower() == "true":
        return base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO3qv/0AAAAASUVORK5CYII="
        )
    prompt = IMAGE_PROMPT.format(topic=topic)
    url = os.getenv("IMAGE_API_URL")
    if not url:
        raise RuntimeError("IMAGE_API_URL non impostata. Configura l'endpoint 4oImageAPI.")
    headers = {"Content-Type": "application/json"}
    key = os.getenv("IMAGE_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    payload = {"prompt": prompt, "size": "1024x576"}
    r = requests.post(url, json=payload, headers=headers, timeout=120)
    r.raise_for_status()
    ctype = r.headers.get("content-type", "")
    if ctype.startswith("image/"):
        return r.content
    try:
        data = r.json()
    except Exception:
        raise RuntimeError("Risposta dall'API immagini non valida")

    b64 = None
    if isinstance(data, dict):
        b64 = data.get("b64") or data.get("b64_png") or data.get("b64_jpg") or data.get("b64_json")
        if not b64 and "data" in data and isinstance(data["data"], list) and data["data"]:
            b64 = data["data"][0].get("b64_json")
        url2 = data.get("url") or data.get("image_url")
        if not b64 and url2:
            r2 = requests.get(url2, timeout=120)
            r2.raise_for_status()
            return r2.content
    if b64:
        return base64.b64decode(b64)
    raise RuntimeError("Formato di risposta immagini non riconosciuto")


def pick_topic(existing: List[dict]) -> str:
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
    load_dotenv(ROOT / ".env")
    ensure_dirs()
    posts = load_posts()

    groq_client = get_groq_client()

    try:
        max_attempts = int(os.getenv("MAX_ATTEMPTS", "4"))
    except ValueError:
        max_attempts = 4

    for attempt in range(1, max_attempts + 1):
        topic = pick_topic(posts["posts"])
        article, body_html = generate_article(groq_client, topic)
        title = article.get("title", topic)
        summary = article.get("summary", "")
        candidate_text = f"{title}\n\n{summary}"

        try:
            sim_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.80"))
        except ValueError:
            sim_threshold = 0.80

        if not too_similar(candidate_text, posts["posts"], sim_threshold):
            break
        if attempt == max_attempts:
            title += f" ({datetime.now(timezone.utc).strftime('%Y-%m-%d')})"

    img_bytes = generate_image(topic)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = slugify(title) or slugify(topic) or f"post-{date_str}"

    img_name = f"{date_str}-{slug}.png"
    img_path = ASSETS / img_name
    with open(img_path, "wb") as f:
        f.write(img_bytes)

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

    post_record = {
        "title": title,
        "summary": summary,
        "date": date_str,
        "read_minutes": read_minutes,
        "tags": article.get("tags", []),
        "image": f"assets/images/{img_name}",
        "path": f"articles/{art_name}",
        "topic": topic,
    }
    posts["posts"].append(post_record)
    save_posts(posts)

    if os.getenv("GIT_AUTO_COMMIT", "false").lower() == "true":
        os.system("git add -A")
        os.system(f"git commit -m \"chore: publish article {art_name}\"")
        os.system("git push")

    print(json.dumps({"created": post_record}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
