#!/usr/bin/env python3
"""
Genera articoli tech TLDR automaticamente usando Groq API
Diego Serpelloni - Article Generator Bot
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

def generate_article():
    """Genera articolo usando Groq"""
    from groq import Groq
    
    print("🤖 Connessione a Groq in corso...")
    
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("❌ GROQ_API_KEY non trovata")
    
    print(f"✅ API Key trovata: {api_key[:20]}...")
    
    client = Groq(api_key=api_key)
    
    now = datetime.now()
    print(f"📅 Data: {now.strftime('%Y-%m-%d %H:%M')}")
    
    prompt = """Sei Diego Serpelloni, 22 anni, appassionato di tech e networking.

Scrivi un articolo TLDR (Too Long; Didn't Read) per il tuo blog personale.

FORMATO RICHIESTO (IMPORTANTE - SEGUI ESATTAMENTE):
---
# [Titolo accattivante in italiano]

## TL;DR
[Riassunto in 1-2 righe dell'argomento principale]

## [Sezione 1: Il Problema/Contesto]
[Contenuto con paragrafi naturali]

## [Sezione 2: La Soluzione/Innovazione]
[Contenuto con paragrafi naturali]

## [Sezione 3: Implicazioni Pratiche]
[Contenuto con paragrafi naturali]

## Cosa Aspettarsi
[Conclusione e previsioni]
---

REQUISITI:
- Argomento: Tema tech/AI/DevOps/Networking/Programmazione recente (2025-2026)
- Lunghezza: 800-1200 parole (5-10 minuti lettura)
- Tono: Professionale ma colloquiale, come parlassi a un amico
- Linguaggio: Italiano
- NO AI/automazione menzionata nel testo
- NO emoji, NO markdown speciale, solo intestazioni # e paragrafi

Scrivi SOLO il contenuto articolo."""

    print("✍️ Generazione articolo...")
    
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        max_tokens=2500
    )
    
    content = chat_completion.choices[0].message.content
    print(f"✅ Articolo generato ({len(content)} caratteri)")
    return content


def parse_article(markdown_content):
    """Estrae titolo e TL;DR dal markdown"""
    lines = markdown_content.split("\n")
    
    title = ""
    tldr = ""
    
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line.replace("# ", "").strip()
        if line.startswith("## TL;DR"):
            if i + 1 < len(lines):
                tldr = lines[i + 1].strip()
            break
    
    return title, tldr


def create_html_article(markdown_content, timestamp):
    """Converte markdown in HTML con CSS coerente"""
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
        elif line.startswith("* "):
            body_lines.append(f"<li>{line.replace('* ', '').strip()}</li>")
        elif line.strip():
            body_lines.append(f"<p>{line.strip()}</p>")
    
    # Raggruppa li in ul
    body_html = ""
    in_list = False
    for line in body_lines:
        if line.startswith("<li>"):
            if not in_list:
                body_html += "<ul>"
                in_list = True
            body_html += line
        else:
            if in_list:
                body_html += "</ul>"
                in_list = False
            body_html += line
    if in_list:
        body_html += "</ul>"
    
    readable_date = timestamp.strftime('%d %b %Y, %H:%M')
    
    html_template = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="author" content="Diego Serpelloni">
    <meta name="description" content="{tldr[:160] if tldr else 'Article by Diego Serpelloni'}">
    <title>{title} | Diego's Tech Blog</title>
    <link rel="stylesheet" href="../../styles/blog.css">
</head>
<body>
    <div class="page">
        <a href="../../index.html" class="back-link">← Torna agli articoli</a>
        
        <article class="article">
            <header class="article-header">
                <h1>{title}</h1>
                <div class="article-meta">
                    <span class="author">Diego Serpelloni</span>
                    <span class="separator">•</span>
                    <span class="date">{readable_date}</span>
                    <span class="separator">•</span>
                    <span class="read-time">5–10 min</span>
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
        
        <a href="../../index.html" class="back-link" style="margin-top: 30px;">← Torna agli articoli</a>
    </div>
</body>
</html>"""
    
    return html_template, title, tldr


def save_article(html_content, timestamp):
    """Salva articolo con timestamp"""
    repo_root = Path(__file__).parent.parent
    articles_dir = repo_root / "articles"
    articles_dir.mkdir(exist_ok=True)
    
    slug = timestamp.strftime("%Y-%m-%d-%H-%M")
    article_path = articles_dir / f"{slug}.html"
    article_path.write_text(html_content, encoding="utf-8")
    
    print(f"💾 Articolo salvato: {slug}.html")
    return slug


def get_all_articles():
    """Legge tutti gli articoli ordinati per data (più recenti prima)"""
    repo_root = Path(__file__).parent.parent
    articles_dir = repo_root / "articles"
    
    if not articles_dir.exists():
        return []
    
    files = sorted(articles_dir.glob("*.html"), reverse=True)
    articles = []
    
    for file in files:
        try:
            content = file.read_text(encoding="utf-8")
            # Estrai titolo e data dal file HTML
            import re
            title_match = re.search(r'<h1>(.*?)</h1>', content)
            date_match = re.search(r'<span class="date">(.*?)</span>', content)
            
            title = title_match.group(1) if title_match else "Senza titolo"
            date_str = date_match.group(1) if date_match else ""
            
            articles.append({
                'slug': file.stem,
                'title': title,
                'date': date_str,
                'filename': file.name
            })
        except:
            pass
    
    return articles


def generate_index_html(articles):
    """Genera l'index con paginazione (10 articoli per pagina)"""
    articles_per_page = 10
    total_pages = (len(articles) + articles_per_page - 1) // articles_per_page
    
    # Pagina 1
    current_articles = articles[:articles_per_page]
    
    post_list_html = ""
    for article in current_articles:
        post_list_html += f'''
          <li class="post-item">
            <a href="articles/{article['slug']}.html" class="post-card">
              <div class="post-meta">
                <span class="post-date">{article['date']}</span>
                <span class="post-dot">•</span>
                <span class="post-readtime">5–10 min</span>
              </div>
              <h3 class="post-title">{article['title']}</h3>
              <div class="post-tags">
                <span class="chip small">Tech</span>
              </div>
            </a>
          </li>'''
    
    pagination_html = ""
    if total_pages > 1:
        pagination_html = '<div class="pagination">'
        if total_pages > 1:
            pagination_html += f'<a href="page2.html" class="page-link">Articoli precedenti →</a>'
        pagination_html += '</div>'
    
    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Diego Serpelloni – Tech Blog</title>
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
        <p class="hero-subtitle">
          22 anni, appassionato di sistemi, networking e sviluppo web.
          Qui appunto quello che imparo smanettando tra server, codice e infrastrutture.
        </p>
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
          <p class="section-subtitle">
            Appunti veloci su quello che sto studiando o testando ultimamente.
          </p>
        </div>
        <ul class="post-list">
{post_list_html}
        </ul>
        {pagination_html}
      </section>
    </main>

    <footer class="site-footer">
      <p>© 2026 Diego Serpelloni</p>
      <p class="footer-sub">Costruito tra una lezione e l'altra, con tanta caffeina.</p>
    </footer>
  </div>
</body>
</html>"""
    
    return html_content, total_pages


def generate_page_n_html(articles, page_num):
    """Genera pagine di archivio (page2.html, page3.html, ecc.)"""
    articles_per_page = 10
    start = (page_num - 1) * articles_per_page
    end = start + articles_per_page
    current_articles = articles[start:end]
    total_pages = (len(articles) + articles_per_page - 1) // articles_per_page
    
    post_list_html = ""
    for article in current_articles:
        post_list_html += f'''
          <li class="post-item">
            <a href="articles/{article['slug']}.html" class="post-card">
              <div class="post-meta">
                <span class="post-date">{article['date']}</span>
                <span class="post-dot">•</span>
                <span class="post-readtime">5–10 min</span>
              </div>
              <h3 class="post-title">{article['title']}</h3>
              <div class="post-tags">
                <span class="chip small">Tech</span>
              </div>
            </a>
          </li>'''
    
    pagination_html = '<div class="pagination">'
    pagination_html += f'<a href="index.html" class="page-link">← Inizio</a>'
    
    if page_num > 2:
        pagination_html += f'<a href="page{page_num - 1}.html" class="page-link">← Precedenti</a>'
    
    pagination_html += f'<span class="page-info">Pagina {page_num} di {total_pages}</span>'
    
    if page_num < total_pages:
        pagination_html += f'<a href="page{page_num + 1}.html" class="page-link">Successivi →</a>'
    
    pagination_html += '</div>'
    
    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Archivio – Diego Serpelloni – Tech Blog</title>
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
{post_list_html}
        </ul>
        {pagination_html}
      </section>
    </main>

    <footer class="site-footer">
      <p>© 2026 Diego Serpelloni</p>
      <p class="footer-sub">Costruito tra una lezione e l'altra, con tanta caffeina.</p>
    </footer>
  </div>
</body>
</html>"""
    
    return html_content


def update_all_pages():
    """Rigenera tutte le pagine di indice e archivio"""
    articles = get_all_articles()
    articles_per_page = 10
    total_pages = (len(articles) + articles_per_page - 1) // articles_per_page
    
    repo_root = Path(__file__).parent.parent
    
    # Pagina 1 (index.html)
    index_html, _ = generate_index_html(articles)
    index_path = repo_root / "index.html"
    index_path.write_text(index_html, encoding="utf-8")
    print("✅ index.html aggiornato")
    
    # Pagine di archivio (page2.html, page3.html, ecc.)
    for page_num in range(2, total_pages + 1):
        page_html = generate_page_n_html(articles, page_num)
        page_path = repo_root / f"page{page_num}.html"
        page_path.write_text(page_html, encoding="utf-8")
        print(f"✅ page{page_num}.html aggiornato")


def main():
    """Main"""
    print("=" * 60)
    print("🤖 Article Generator")
    print("=" * 60)
    
    try:
        now = datetime.now()
        
        # Genera articolo
        article_content = generate_article()
        
        # Parse e crea HTML
        print("🎨 Creazione HTML...")
        html_article, title, tldr = create_html_article(article_content, now)
        
        # Salva articolo
        slug = save_article(html_article, now)
        
        # Rigenera tutte le pagine
        print("📄 Rigenerazione indici...")
        update_all_pages()
        
        print("\n" + "=" * 60)
        print(f"✅ SUCCESSO!")
        print(f"   Articolo: {slug}.html")
        print(f"   Titolo: {title}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERRORE: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
