# Tech Blog Automation (PCB Style)

Questo progetto genera un blog tech statico con estetica PCB e pubblica automaticamente un articolo al giorno usando Perplexity API per i contenuti.

## Funzionalita principali
- Static site con Markdown + frontmatter.
- Generazione giornaliera di contenuti.
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
   - `PERPLEXITY_API_KEY`
   - `PERPLEXITY_TEXT_MODEL` (default `sonar-pro`)
   - `PERPLEXITY_FALLBACK_MODELS` (default `sonar`)
   - `PERPLEXITY_MAX_TOKENS` (default `1800`)
   - `DEFAULT_COVER_IMAGE` (default `assets/images/pcb-bg.png`)
   - `SITE_BASE_URL`
3. Genera articolo e build:
   - `python scripts/generate_daily.py`
   - `python scripts/build_site.py`

## Topics e log
- Modifica `data/topics.json` per cambiare i temi.
- Lo storico e in `data/generated_log.json`.

## Automazione con GitHub Actions
Configura:
- Secret `PERPLEXITY_API_KEY`
- Vars `PERPLEXITY_TEXT_MODEL`, `PERPLEXITY_FALLBACK_MODELS`, `PERPLEXITY_MAX_TOKENS`, `SITE_BASE_URL`

Il workflow `.github/workflows/daily.yml` esegue la generazione e il build giornaliero.

## Troubleshooting
- **Quota OpenAI**: lo script termina con exit code 0 e logga un messaggio chiaro. Verifica billing/limiti.
- **Build incompleto**: esegui `python scripts/build_site.py`.
- **Immagini**: la cover usa un file locale (`DEFAULT_COVER_IMAGE`). Puoi sostituirlo manualmente per ogni articolo.

## Note Instagram
Lo script `scripts/publish_instagram.py` usa `data/posts.json` per prendere l ultimo articolo e l immagine relativa.
