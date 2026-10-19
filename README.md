# Mue

> *Comme un serpent qui change de peau, ton CV mue pour chaque offre.*

Application locale et personnelle : analyse d'offre (go / no-go), CV adapté et lettre de motivation en PDF, audit du CV,
historique des candidatures. L'IA passe par **Claude Code en mode headless** (`claude -p`) avec l'abonnement Claude, sans clé API.
Voir [SPEC.md](SPEC.md).

## Prérequis

- Python 3.12+ et Node 20+
- Claude Code : `npm install -g @anthropic-ai/claude-code`, connecté (`claude` puis `/login`) **ou** un token dans `.env`
- Typst : rien à installer, le compilateur est embarqué par le paquet Python `typst`

## Installation et lancement

```powershell
.\dev.ps1 install   # venv, dépendances, migrations, .env créé depuis .env.example
.\dev.ps1           # API (8040) + worker Huey + front (5173)
.\dev.ps1 test      # pytest + typecheck
```

Ou avec make : `make install`, `make dev`, `make test`.

Puis ouvrir <http://localhost:5173>.

## Configuration (`.env`)

| Variable                  | Rôle                                                         |
|---------------------------|--------------------------------------------------------------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Token longue durée (`claude setup-token`). Vide = session locale |
| `MUE_CLAUDE_MODEL`        | Modèle passé à `--model` (défaut `sonnet`)                   |
| `MUE_CLAUDE_TIMEOUT`      | Timeout d'un appel, en secondes (défaut 120)                 |
| `MUE_API_PORT`            | Port de l'API vu par le proxy Vite (défaut 8040)             |

## Organisation

```
backend/
  core/claude_client.py   appel `claude -p` (stdin), extraction JSON, validation Pydantic + 1 retry, verrou, logs
  core/schemas.py         schémas : profil, analyse, CV, lettre, audit
  core/guard.py           garde-fou anti-invention déterministe
  core/pdf.py             rendu Typst
  core/jobs.py            exécution des jobs (Huey, un seul worker = un appel Claude à la fois)
  core/profile_service.py versions du profil + miroir data/profile.yaml
frontend/src/pages/       Accueil, Nouvelle offre, Candidature (CV / Lettre), Profil, Audit
prompts/*.md              prompts éditables ({{profil}}, {{offre}}, {{schema}}…)
typst/default/            templates CV et lettre
data/                     SQLite, PDF, uploads, profile.yaml (non versionné)
logs/claude/              prompt, réponse, durée et coût de chaque appel (non versionné)
```

## Points notables

- **Profil maître** : chaque enregistrement crée une version (rollback depuis l'écran Profil). `data/profile.yaml` est
  réécrit à chaque version ; une modification à la main est détectée au prochain chargement et enregistrée comme nouvelle version.
- **Import de CV** : l'extraction est un brouillon, rien n'est enregistré avant « Valider l'import ».
- **Analyse** : si le verdict est favorable, la génération du CV s'enchaîne automatiquement ; si c'est `ne_pas_postuler`,
  rien ne se lance et le bouton « Générer quand même » reste disponible.
- **Garde-fou** : entreprise, diplôme ou date absents du profil → erreur ; compétence ou chiffre absents → avertissement.
  Il est relancé à chaque édition manuelle.
- **Audit** : une suggestion acceptée ne s'applique qu'à un champ texte du profil et seulement s'il y a une réécriture ;
  le reste est traité comme une remarque globale.
- **Erreurs Claude** (timeout, limite d'usage, token expiré) : message explicite et bouton « Relancer ».
