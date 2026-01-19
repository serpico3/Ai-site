---
title: "Permessi Linux in laboratorio scolastico: guida pratica"
date: "2026-01-19"
tags:
  - linux
  - permessi
  - sysadmin
  - sicurezza
  - storage
slug: "permessi-linux-laboratorio-scolastico"
excerpt: "Come impostare utenti, gruppi e permessi per la cartella studenti senza caos e senza rischi."
cover_image: "assets/images/chip.svg"
author: "Diego"
---

## Introduzione
Nel laboratorio scolastico i permessi non sono un dettaglio: sono la base per evitare cancellazioni accidentali, accessi impropri e problemi di privacy. Qui trovi una guida pratica, pensata per contesti reali con cartelle studenti, cartella pubblica e docenti.

## Scenario reale
Hai un server Linux che ospita le home degli studenti su uno storage condiviso. Ogni classe ha una cartella, esiste una cartella pubblica per consegne e un gruppo docenti che deve avere accesso in lettura a tutto. Serve ordine, tracciabilita e pochi ticket.

## Procedura step-by-step
1. Crea i gruppi base (studenti, docenti, classi).
2. Struttura le directory con ownership chiaro.
3. Applica permessi e ACL per eccezioni.
4. Blocca l ereditarieta sbagliata con setgid dove serve.
5. Verifica con un utente di test.

## Comandi
```bash
sudo groupadd studenti
sudo groupadd docenti
sudo groupadd classe3a

sudo mkdir -p /srv/scuola/{studenti,docenti,consegne}
sudo chown root:docenti /srv/scuola/docenti
sudo chmod 2770 /srv/scuola/docenti

sudo chown root:studenti /srv/scuola/studenti
sudo chmod 2770 /srv/scuola/studenti

sudo setfacl -m g:docenti:rx /srv/scuola/studenti
sudo setfacl -d -m g:docenti:rx /srv/scuola/studenti
```

## Errori comuni e fix
- Permessi troppo larghi: usa 2770 invece di 2777.
- Gruppi non coerenti: standardizza i nomi e documenta.
- Mancanza di ACL: per eccezioni usa setfacl, non chmod random.

## Hardening / Sicurezza
- Separa rete didattica e amministrazione con VLAN.
- Abilita audit su cartelle sensibili.
- Aggiorna regolarmente il server e limita l accesso SSH con chiavi.

## Checklist
- [ ] Gruppi creati e documentati
- [ ] Cartelle con setgid dove serve
- [ ] ACL applicate per docenti
- [ ] Utente test validato
- [ ] Backup attivo

## Mini glossario
- ACL: permessi aggiuntivi oltre a owner e gruppo.
- setgid: eredita il gruppo della directory.
- umask: maschera di permessi di default.
- ownership: proprietario e gruppo di un file.
- hardening: riduzione della superficie di attacco.

## Conclusione
Con una struttura semplice e coerente eviti errori quotidiani e migliori la sicurezza. Se standardizzi gruppi e permessi, il laboratorio diventa stabile e facile da gestire.
