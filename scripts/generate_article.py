#!/usr/bin/env python3
"""
Genera articoli tech TLDR automaticamente usando Groq API
Diego Serpelloni - Article Generator Bot
"""

import os
import json
from datetime import datetime
from pathlib import Path
from groq import Groq

def get_groq_client():
    """Inizializza client Groq"""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY non trovata nelle environment variables")
    return Groq(api_key=api_key)

def generate_article():
    """Genera articolo usando Groq"""
    client = get_groq_client()
    
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    
    # Prompt per generare articolo TLDR
    prompt = """Sei Diego Serpelloni, un ragazzo di 22 anni, esperto di informatica e networking con una laurea in informatica.
    
Genera un articolo tech TLDR (Too Long; Didn't Read) per il tuo blog personale.

REQUISITI:
- Argomento: Una notizia/trend/scoperta recente nel mondo della tecnologia, AI, DevOps, networking o programmazione
- Formato: TLDR (riassunto conciso e impattante)
- Lunghezza: 5-10 minuti di lettura (circa 800-1200 parole)
- Tono: Professionale ma colloquiale, da esperto giovane
- Struttura:
  1. Titolo accattivante
  2. TL;DR (riassunto in 1-2 righe)
  3. Il Problema/Contesto
  4. La Soluzione/Innovazione
  5. Implicazioni Pratiche
  6. Cosa Aspettarsi
  7. Link/Risorse (crea URL plausibili)

Scrivi in markdown. Sii specifico, tecnico ma comprensibile. Aggiungi dettagli che solo un esperto di networking darebbe.

Risponi SOLO con il contenuto dell'articolo, senza cornice."""

    message = client.messages.create(
        model="mixtral-8x7b-32768",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return message.content.text

def create_html_article(markdown_content, date_str):
    """Converte il contenuto in HTML stilizzato"""
    
    # Parsing semplice del markdown
    lines = markdown_content.split("\n")
    
    title = ""
    tldr = ""
    body_lines = []
    
    in_tldr = False
    skip_next = False
    
    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue
            
        if line.startswith("# "):
            title = line.replace("# ", "").strip()
        elif line.startswith("## TL;DR") or line.startswith("## TL;DR:"):
            in_tldr = True
            skip_next = True
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
    <div class="container">
        <article class="article">
            <header class="article-header">
                <h1>{title}</h1>
                <div class="article-meta">
                    <span class="author">Diego Serpelloni</span>
                    <span class="date">{datetime.strptime(date_str, '%Y-%m-%d').strftime('%d %b %Y')}</span>
                    <span class="read-time">📖 5-10 min read</span>
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
                    <span class="tag">#tech</span>
                    <span class="tag">#networking</span>
                    <span class="tag">#devops</span>
                </div>
                <div class="share">
                    <a href="https://twitter.com/share?url=https://serpico3.github.io/Ai-site/articles/{date_str}.html&text={title}" target="_blank">Share on Twitter</a>
                </div>
            </footer>
        </article>
    </div>
</body>
</html>"""
    
    return html_template

def save_article(html_content, date_str):
    """Salva articolo in cartella articles"""
    articles_dir = Path("articles")
    articles_dir.mkdir(exist_ok=True)
    
    article_path = articles_dir / f"{date_str}.html"
    article_path.write_text(html_content, encoding="utf-8")
    
    return str(article_path)

def update_index(date_str):
    """Aggiorna index.html con il nuovo articolo"""
    index_path = Path("index.html")
    
    # Se l'index non esiste, lo creiamo
    if not index_path.exists():
        create_default_index()
    
    content = index_path.read_text(encoding="utf-8")
    
    # Inserisce il nuovo articolo nella lista
    new_entry = f'<li><a href="articles/{date_str}.html">{datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %b %Y")}</a></li>'
    
    # Inserisce prima della chiusura di </ul>
    content = content.replace("</ul>", f"{new_entry}\n</ul>", 1)
    
    index_path.write_text(content, encoding="utf-8")

def create_default_index():
    """Crea index.html di default se non esiste"""
    index_content = """<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Diego's Tech Blog</title>
    <link rel="stylesheet" href="styles/blog.css">
</head>
<body>
    <div class="container">
        <header class="blog-header">
            <h1>🚀 Diego's Tech Blog</h1>
            <p>Articoli tech, networking, DevOps e programmazione</p>
            <p><strong>Auto-generated daily at 15:00 CET</strong></p>
        </header>
        
        <main>
            <section class="articles">
                <h2>Latest Articles</h2>
                <ul>
                </ul>
            </section>
        </main>
        
        <footer class="blog-footer">
            <p>© 2026 Diego Serpelloni | Powered by Groq + GitHub Actions</p>
            <p><a href="https://github.com/serpico3">GitHub</a></p>
        </footer>
    </div>
</body>
</html>"""
    
    Path("index.html").write_text(index_content, encoding="utf-8")

def main():
    """Main function"""
    print("🤖 Generating article with Groq...")
    
    try:
        # Genera articolo
        article_content = generate_article()
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Crea HTML
        html_article = create_html_article(article_content, today)
        
        # Salva articolo
        article_path = save_article(html_article, today)
        print(f"✅ Article saved: {article_path}")
        
        # Aggiorna index
        update_index(today)
        print(f"✅ Index updated")
        
        print(f"\n📰 Article generated successfully!")
        print(f"Date: {today}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
