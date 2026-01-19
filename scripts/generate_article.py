#!/usr/bin/env python3
"""
Generatore articoli per il blog (Groq API) + pagine indice/archivio.
"""

import os
import sys
import re
from datetime import datetime
from pathlib import Path


def generate_article():
    """Genera articolo usando Groq."""
    from groq import Groq

    print("Connessione a Groq in corso...")
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY non trovata")
    print(f"API Key trovata: {api_key[:12]}...")

    client = Groq(api_key=api_key)
    now = datetime.now()
    print(f"Data: {now.strftime('%Y-%m-%d %H:%M')}")

    prompt = """Sei Diego Serpelloni (22 anni), appassionato di sistemi, networking e sviluppo web.

Scrivi un articolo in italiano per il tuo blog personale, chiaro e utile anche a lettori non esperti.

Formato richiesto (segui esattamente):
# [Titolo accattivante]

## TL;DR
[Riassunto in 1–2 frasi sull'idea centrale]

## Contesto
[Definisci perché l'argomento è rilevante ora e per chi]

## Concetti chiave
- [Elenco puntato sintetico (3–5 voci)]

## Come funziona
[Spiegazione pratica con esempi reali e comandi/strumenti se utili]

## Best practice
- [Consigli e insidie comuni]

## Casi d'uso
[2–3 scenari concreti]

## Prossimi passi
[Checklist pratica per iniziare]

Requisiti di stile:
- Lunghezza: circa 1200–1600 parole
- Linguaggio: italiano chiaro, tono amichevole e professionale
- Niente menzioni all'uso di AI o automazione
- Usa solo intestazioni (#, ##, ###), paragrafi e liste con "- "; niente tabelle o link fittizi
- Non inventare fonti; nessun riferimento a ricerche in tempo reale

Scrivi SOLO il contenuto dell'articolo, senza testo extra."""

    print("Generazione articolo...")
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        max_tokens=1800,
        temperature=0.8,
    )
    content = chat_completion.choices[0].message.content
    print(f"Articolo generato ({len(content)} caratteri)")
    return content


def create_html_article(markdown_content: str, timestamp: datetime):
    """Converte markdown (ridotto) in HTML con stile coerente."""
    lines = markdown_content.split("\n")
    title = ""
    tldr = ""
    body_lines = []
    in_tldr = False
    for line in lines:
        if line.startswith("# "):
            title = line.replace("# ", "").strip()
        elif line.startswith("## TL;DR"):
            in_tldr = True
            continue
        elif in_tldr and line.strip():
            tldr = line.strip()
            in_tldr = False
        elif line.startswith("## "):
            body_lines.append(f"<h2>{line.replace('## ', '').strip()}</h2>")
        elif line.startswith("### "):
            body_lines.append(f"<h3>{line.replace('### ', '').strip()}</h3>")
        elif line.startswith("- "):
            body_lines.append(f"<li>{line.replace('- ', '').strip()}</li>")
        elif line.strip():
            body_lines.append(f"<p>{line.strip()}</p>")

    # chiudi/avvia liste
    body_html = ""
    in_list = False
    for frag in body_lines:
        if frag.startswith("<li>"):
            if not in_list:
                body_html += "<ul>"
                in_list = True
            body_html += frag
        else:
            if in_list:
                body_html += "</ul>"
                in_list = False
            body_html += frag
    if in_list:
        body_html += "</ul>"

    # stima lettura
    plain = re.sub(r"<[^>]+>", " ", body_html)
    words = len([w for w in plain.split() if w.strip()])
    read_time_min = max(1, (words + 179) // 180)

    readable_date = timestamp.strftime('%d %b %Y, %H:%M')

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="author" content="Diego Serpelloni">
    <meta name="description" content="{tldr[:160] if tldr else 'Article by Diego Serpelloni'}">
    <title>{title} | Diego's Tech Blog</title>
    <link rel="stylesheet" href="../styles/blog.css">
</head>
<body>
    <div class="page">
        <a href="../index.html" class="back-link">&larr; Torna agli articoli</a>
        <article class="article">
            <header class="article-header">
                <h1>{title}</h1>
                <div class="article-meta">
                    <span class="author">Diego Serpelloni</span>
                    <span class="separator">&middot;</span>
                    <span class="date">{readable_date}</span>
                    <span class="separator">&middot;</span>
                    <span class="read-time">{read_time_min} min</span>
                </div>
                <div class="tldr">
                    <strong>TL;DR:</strong> {tldr}
                </div>
            </header>
            <main class="article-content">
                {body_html}
            </main>
            <footer class="article-footer">
                <div class="tags">
                    <span class="chip">Tech</span>
                    <span class="chip">Appunti</span>
                </div>
            </footer>
        </article>
        <a href="../index.html" class="back-link" style="margin-top: 30px;">&larr; Torna agli articoli</a>
    </div>
</body>
</html>"""
    return html, title, tldr


def save_article(html_content: str, timestamp: datetime):
    repo_root = Path(__file__).parent.parent
    articles_dir = repo_root / "articles"
    articles_dir.mkdir(exist_ok=True)
    slug = timestamp.strftime("%Y-%m-%d-%H-%M")
    path = articles_dir / f"{slug}.html"
    path.write_text(html_content, encoding="utf-8")
    print(f"Articolo salvato: {slug}.html")
    return slug


def get_all_articles():
    repo_root = Path(__file__).parent.parent
    articles_dir = repo_root / "articles"
    if not articles_dir.exists():
        return []
    files = sorted(articles_dir.glob("*.html"), reverse=True)
    out = []
    for f in files:
        try:
            content = f.read_text(encoding="utf-8")
            title = re.search(r'<h1>(.*?)</h1>', content)
            date = re.search(r'<span class="date">(.*?)</span>', content)
            body = re.search(r'<main class="article-content">(.*?)</main>', content, re.S)
            text = re.sub(r'<[^>]+>', ' ', body.group(1) if body else content)
            words = len([w for w in text.split() if w.strip()])
            read_time = max(1, (words + 179) // 180)
            out.append({
                'slug': f.stem,
                'title': title.group(1) if title else 'Senza titolo',
                'date': date.group(1) if date else '',
                'read_time': read_time,
            })
        except Exception:
            pass
    return out


def generate_index_html(articles):
    articles_per_page = 10
    total_pages = (len(articles) + articles_per_page - 1) // articles_per_page
    current = articles[:articles_per_page]

    posts = ""
    for a in current:
        posts += f'''\n          <li class="post-item">\n            <a href="articles/{a['slug']}.html" class="post-card">\n              <div class="post-meta">\n                <span class="post-date">{a['date']}</span>\n                <span class="post-dot">&middot;</span>\n                <span class="post-readtime">{a.get('read_time', 5)} min</span>\n              </div>\n              <h3 class="post-title">{a['title']}</h3>\n              <div class="post-tags">\n                <span class="chip small">Tech</span>\n              </div>\n            </a>\n          </li>'''

    pagination = ""
    if total_pages > 1:
        pagination = '<div class="pagination">'
        pagination += '<a href="page2.html" class="page-link">Articoli precedenti &rarr;</a>'
        pagination += '</div>'

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Diego Serpelloni - Tech Blog</title>
  <link rel="stylesheet" href="styles/blog.css" />
</head>
<body>
  <div class="page">
    <header class="hero">
      <div class="hero-left">
        <div class="avatar">DS</div>
      </div>
      <div class="hero-right">
        <h1>Diego Serpelloni</h1>
        <p class="hero-subtitle">22 anni, appassionato di sistemi, networking e sviluppo web.\n          Qui appunto quello che imparo smanettando tra server, codice e infrastrutture.</p>
        <div class="hero-tags">
          <span class="chip">Linux</span>
          <span class="chip">Networking</span>
          <span class="chip">DevOps</span>
          <span class="chip">Web Dev</span>
        </div>
        <nav class="hero-links">
          <a href="https://github.com/serpico3" target="_blank" rel="noreferrer">GitHub</a>
          <a href="mailto:diego@example.com">Contattami</a>
        </nav>
      </div>
    </header>

    <main>
      <section class="section">
        <div class="section-header">
          <h2>Articoli recenti</h2>
          <p class="section-subtitle">Appunti veloci su quello che sto studiando o testando ultimamente.</p>
        </div>
        <ul class="post-list">
{posts}
        </ul>
        {pagination}
      </section>
    </main>

    <footer class="site-footer">
      <p>&copy; 2026 Diego Serpelloni</p>
      <p class="footer-sub">Costruito tra una lezione e l'altra, con tanta caffeina.</p>
    </footer>
  </div>
</body>
</html>"""
    return html, total_pages


def generate_page_n_html(articles, page_num: int):
    per_page = 10
    start = (page_num - 1) * per_page
    end = start + per_page
    current = articles[start:end]
    total_pages = (len(articles) + per_page - 1) // per_page

    posts = ""
    for a in current:
        posts += f'''\n          <li class="post-item">\n            <a href="articles/{a['slug']}.html" class="post-card">\n              <div class="post-meta">\n                <span class="post-date">{a['date']}</span>\n                <span class="post-dot">&middot;</span>\n                <span class="post-readtime">{a.get('read_time', 5)} min</span>\n              </div>\n              <h3 class="post-title">{a['title']}</h3>\n              <div class="post-tags">\n                <span class="chip small">Tech</span>\n              </div>\n            </a>\n          </li>'''

    pagination = '<div class="pagination">'
    pagination += '<a href="index.html" class="page-link">&larr; Inizio</a>'
    if page_num > 2:
        pagination += f'<a href="page{page_num - 1}.html" class="page-link">&larr; Precedenti</a>'
    pagination += f'<span class="page-info">Pagina {page_num} di {total_pages}</span>'
    if page_num < total_pages:
        pagination += f'<a href="page{page_num + 1}.html" class="page-link">Successivi &rarr;</a>'
    pagination += '</div>'

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Archivio - Diego Serpelloni - Tech Blog</title>
  <link rel="stylesheet" href="styles/blog.css" />
</head>
<body>
  <div class="page">
    <header class="hero" style="margin-bottom: 30px;">
      <div class="hero-left">
        <div class="avatar">DS</div>
      </div>
      <div class="hero-right">
        <h1>Archivio</h1>
        <p class="hero-subtitle">Articoli precedenti</p>
      </div>
    </header>

    <main>
      <section class="section">
        <ul class="post-list">
{posts}
        </ul>
        {pagination}
      </section>
    </main>

    <footer class="site-footer">
      <p>&copy; 2026 Diego Serpelloni</p>
      <p class="footer-sub">Costruito tra una lezione e l'altra, con tanta caffeina.</p>
    </footer>
  </div>
</body>
</html>"""
    return html


def update_all_pages():
    articles = get_all_articles()
    repo_root = Path(__file__).parent.parent
    index_html, total_pages = generate_index_html(articles)
    (repo_root / "index.html").write_text(index_html, encoding="utf-8")
    print("index.html aggiornato")
    for page in range(2, total_pages + 1):
        page_html = generate_page_n_html(articles, page)
        (repo_root / f"page{page}.html").write_text(page_html, encoding="utf-8")
        print(f"page{page}.html aggiornato")


def main():
    print("=" * 60)
    print("Article Generator")
    print("=" * 60)
    mode = (sys.argv[1] if len(sys.argv) > 1 else "generate").lower()
    try:
        if mode == "reindex":
            print("Rigenerazione indici...")
            update_all_pages()
            print("Completato.")
            return

        now = datetime.now()
        content = generate_article()
        print("Creazione HTML...")
        html, title, tldr = create_html_article(content, now)
        slug = save_article(html, now)
        print("Rigenerazione indici...")
        update_all_pages()
        print("\n" + "=" * 60)
        print("SUCCESSO!")
        print(f"   Articolo: {slug}.html")
        print(f"   Titolo: {title}")
        print("=" * 60)
    except Exception as e:
        print(f"\nERRORE: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

