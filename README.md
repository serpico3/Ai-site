# Blog Tech Automatico con OpenAI

Questo progetto crea e pubblica automaticamente, ogni giorno alle 15:00, un articolo tech (~5 minuti di lettura) con un'immagine di copertina generata da OpenAI. Gli articoli non si ripetono grazie a un controllo di similarità basato su embedding.

## Requisiti
- Python 3.10+
- `pip`
- Chiave API OpenAI (`OPENAI_API_KEY`)
- (Opzionale) Git configurato con `origin` remoto per pubblicazione automatica

## Setup
1. Crea un virtual env e installa le dipendenze:
   - Windows PowerShell
     - `python -m venv .venv`
     - `.venv\\Scripts\\Activate.ps1`
     - `pip install -r requirements.txt`
2. Copia `.env.example` in `.env` e imposta `OPENAI_API_KEY`.
3. (Opzionale) Imposta variabili nel `.env`:
   - `OPENAI_MODEL_TEXT` (default: `gpt-4o-mini`)
   - `OPENAI_MODEL_IMAGE` (default: `gpt-image-1`)
   - `OPENAI_MODEL_EMBED` (default: `text-embedding-3-small`)
   - `LANG` (default: `it`)
   - `GIT_AUTO_COMMIT` = `true|false` (default `false`)
   - `DRY_RUN` = `true|false` per test senza chiamare le API

## Esecuzione manuale
- `python scripts/generate_daily.py` genera un nuovo articolo, immagine e aggiorna l'index.

## Pianificazione (15:00 ogni giorno)

### Opzione consigliata: GitHub Actions
Esegui automaticamente nel repo remoto con una Secret:

- Aggiungi la secret `OPENAI_API_KEY` nel repository (Settings → Secrets and variables → Actions → New repository secret).
- Il workflow `.github/workflows/daily.yml` fa partire la generazione ogni giorno alle 15:00 (Europe/Rome) e fa push dei file statici.
- Puoi forzare l'esecuzione anche da `Actions → Daily Publish → Run workflow`.

### Opzione locale (Windows Task Scheduler)
Se preferisci eseguire in locale:

```
scripts\\register_task.ps1 -Time "15:00"
```

Per rimuovere il task:

```
scripts\\unregister_task.ps1
```

Per lanciare subito una generazione manuale:

```
scripts\\run_daily.ps1
```

## Struttura
- `articles/` HTML generati
- `assets/images/` immagini generate
- `assets/style.css` stile di base
- `data/posts.json` metadati e embedding per anti-duplicazione
- `index.html` elenco degli articoli
- `scripts/` generatori e scheduler

## Note su anti-duplicazione
Il sistema confronta gli embedding (titolo+riassunto) dei candidati con i post già pubblicati e scarta quelli troppo simili (soglia di similarità coseno ~0.88). In caso di collisioni ripete il tentativo con nuove proposte.

## Deployment
Se `GIT_AUTO_COMMIT=true` e c'è un remoto `origin`, al termine della generazione esegue `git add/commit/push`. Puoi usare GitHub Pages o un hosting statico a tua scelta.
