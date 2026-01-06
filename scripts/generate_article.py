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
