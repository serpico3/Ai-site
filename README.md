# Tech Blog Automation (PCB Style)

Questo progetto genera un blog tech statico con estetica PCB e pubblica automaticamente un articolo al giorno con immagine di copertina generata da OpenAI.

## Funzionalita principali
- Static site con Markdown + frontmatter.
- Generazione giornaliera di contenuti e immagini.
- Tag e categorie aggiornati automaticamente.
- SEO completo (canonical, OpenGraph, Twitter Card, JSON-LD, sitemap, robots).
- Nessuna newsletter.

## Struttura
- `content/posts/` articoli Markdown con frontmatter.
- `templates/` layout HTML.
- `article/` pagine articolo generate.
- `articles/` archivio articoli con paginazione.
- `tag/` pagine per tag.
- `categories/` elenco categorie.
- `assets/` CSS, JS e immagini.
- `data/` log e indici generati.

## Setup locale
1. Crea virtualenv e installa dipendenze:
   - `python -m venv .venv`
   - `.venv\\Scripts\\Activate.ps1`
   - `pip install -r requirements.txt`
2. Copia `.env.example` in `.env` e configura:
   - `OPENAI_API_KEY`
   - `OPENAI_TEXT_MODEL` (default `gpt-4o-mini`)
   - `OPENAI_IMAGE_MODEL` (default `gpt-image-1`)
   - `SITE_BASE_URL`
3. Genera articolo e build:
   - `python scripts/generate_daily.py`
   - `python scripts/build_site.py`

## Topics e log
- Modifica `data/topics.json` per cambiare i temi.
- Lo storico e in `data/generated_log.json`.

## Automazione con GitHub Actions
Configura:
- Secret `OPENAI_API_KEY`
- Vars `OPENAI_TEXT_MODEL`, `OPENAI_IMAGE_MODEL`, `SITE_BASE_URL`

Il workflow `.github/workflows/daily.yml` esegue la generazione e il build giornaliero.

## Troubleshooting
- **Quota OpenAI**: lo script termina con exit code 0 e logga un messaggio chiaro. Verifica billing/limiti.
- **Build incompleto**: esegui `python scripts/build_site.py`.
- **Immagini**: assicurati che il modello immagini sia attivo e che `Pillow` sia installato.

## Note Instagram
Lo script `scripts/publish_instagram.py` usa `data/posts.json` per prendere l ultimo articolo e l immagine relativa.
