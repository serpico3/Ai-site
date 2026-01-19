# Blog Tech Automatico con OpenAI

Questo progetto crea e pubblica automaticamente, ogni giorno alle 15:00, un articolo tech (~5 minuti di lettura) con un'immagine di copertina generata da OpenAI. Gli articoli non si ripetono grazie a un controllo di similarità basato su embedding.

## Requisiti
- Python 3.10+
- `pip`
- Opzionale: chiave Groq (`GROQ_API_KEY`) se richiesta dall’endpoint usato
- Endpoint 4oImageAPI per immagini (`IMAGE_API_URL`) — può non richiedere chiavi
- (Opzionale) Git configurato con `origin` remoto per pubblicazione automatica

## Setup
1. Crea un virtual env e installa le dipendenze:
   - Windows PowerShell
     - `python -m venv .venv`
     - `.venv\\Scripts\\Activate.ps1`
     - `pip install -r requirements.txt`
2. Copia `.env.example` in `.env` e imposta, se servono:
   - `GROQ_API_KEY` (opzionale)
   - `GROQ_MODEL_TEXT` (default: `llama-3.1-70b-versatile`)
   - `IMAGE_API_URL` (endpoint 4oImageAPI)
   - `IMAGE_API_KEY` (opzionale)
   - `LANG` (default: `it`)
   - `GIT_AUTO_COMMIT` = `true|false` (default `false`)
   - `DRY_RUN` = `true|false` per test senza chiamare le API

## Esecuzione manuale
- `python scripts/generate_daily.py` genera un nuovo articolo, immagine e aggiorna l'index.

## Pianificazione (15:00 ogni giorno)

### Opzione consigliata: GitHub Actions
Esecuzione automatica nel repo remoto:

- Configura l’endpoint immagini `IMAGE_API_URL` come variabile del workflow o nel codice se pubblico.
- Se l’endpoint Groq richiede chiave, aggiungi la secret `GROQ_API_KEY`.
- Il workflow `.github/workflows/daily.yml` avvia la generazione ogni giorno alle 15:00 (Europe/Rome) e fa push.
- Puoi forzare l'esecuzione da `Actions → Daily Publish → Run workflow`.

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
Il sistema usa TF‑IDF con similarità coseno sul testo (titolo+riassunto) per scartare proposte troppo simili. Soglia predefinita `SIMILARITY_THRESHOLD=0.80`. In mancanza di scikit‑learn, cade su Jaccard.

## Pubblicazione Instagram (workflow separato)
- Workflow: `.github/workflows/instagram.yml` (programmato poco dopo la pubblicazione).
- Script: `scripts/publish_instagram.py` prepara il payload (immagine + caption). Integra poi l’API Instagram Graph nel passaggio successivo come preferisci.

## Deployment
Se `GIT_AUTO_COMMIT=true` e c'è un remoto `origin`, al termine della generazione esegue `git add/commit/push`. Puoi usare GitHub Pages o un hosting statico a tua scelta.
