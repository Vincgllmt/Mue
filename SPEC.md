# Mue — Spécification fonctionnelle et technique

> *Comme un serpent qui change de peau, ton CV mue pour chaque offre.*

**Version** : 0.1 (MVP)
**Auteur** : Vincent
**Date** : 19/10/2026

---

## 1. Objectif

Mue est une application web **locale et personnelle** qui accélère la préparation des candidatures :

1. analyser une offre d'emploi et donner un avis go/no-go ;
2. générer un **CV adapté** et une **lettre de motivation** ciblée, en PDF ;
3. **auditer et améliorer** le CV de référence.
4. Garder un historique des candidatures et des versions du profil.
5. Si possible et non contraire aux CGU, proposer des offres aux titres similaires à partir d'un job board (v2).

L'IA passe par **Claude Code en mode headless**, authentifié avec le token de l'abonnement Claude. Aucune clé API Anthropic n'est utilisée.

### Principes

- **Aucune invention** : l'IA ne fait que sélectionner, reformuler et prioriser ce qui existe dans le profil. Elle n'ajoute jamais d'expérience, de compétence ni de chiffre.
- **Validation humaine** : rien ne part sans relecture. Tout contenu généré reste éditable avant l'export.
- **Usage personnel** : l'app tourne en local, avec un seul utilisateur. Elle n'est pas destinée à être déployée pour des tiers, car le token est celui de l'abonnement personnel.

### Hors périmètre (v1)

- Soumission automatique sur les plateformes (LinkedIn, Indeed, WTTJ, ATS)
- Scraping de job boards
- Multi-utilisateur, authentification

---

## 2. Fonctionnalités

### F1. Profil maître

C'est la source de vérité unique de toutes les générations.

- Fichier `profile.yaml`, éditable dans l'app (formulaire) ou à la main.
- Contenu :
    - identité et contact ;
    - titre et accroche ;
    - expériences : poste, entreprise, dates, contexte, réalisations détaillées, stack ;
    - formations ;
    - compétences : catégorie et niveau ;
    - projets ;
    - langues ;
    - centres d'intérêt.
- Le profil maître est **volontairement exhaustif** : il contient bien plus que ce qui tient sur un CV d'une page, et l'IA fait la sélection.
- Import initial : on dépose un CV PDF ou DOCX existant, Claude l'extrait vers `profile.yaml`, puis l'utilisateur valide l'extraction.

### F2. Analyse d'offre

**Entrée** : texte de l'offre collé. L'URL est optionnelle et stockée pour référence uniquement : pas de fetch automatique en v1, car les job boards bloquent.

**Sortie** (JSON structuré) :

| Champ                                                   | Description                                              |
|---------------------------------------------------------|----------------------------------------------------------|
| `entreprise`, `poste`, `lieu`, `contrat`, `teletravail` | Informations extraites                                   |
| `stack_requise` / `stack_bonus`                         | Technologies obligatoires et souhaitées                  |
| `seniorite`                                             | Niveau attendu (junior / confirmé / senior)              |
| `mots_cles_ats`                                         | Termes à refléter dans le CV                             |
| `score_matching`                                        | Score de 0 à 100                                         |
| `points_forts`                                          | Correspondances avec le profil                           |
| `ecarts`                                                | Prérequis manquants ou faibles                           |
| `verdict`                                               | `postuler` / `postuler_avec_reserve` / `ne_pas_postuler` |
| `justification`                                         | 2 à 4 phrases                                            |

**Règle** : si le verdict est `ne_pas_postuler`, l'app **n'enchaîne pas** sur la génération. Un bouton « Générer quand même » reste disponible.

### F3. Génération du CV adapté

- **Entrées** : profil maître et analyse de l'offre.
- **Traitement par l'IA** :
    - sélection des expériences, projets et compétences pertinents ;
    - réécriture des puces orientée impact, avec le vocabulaire de l'offre quand c'est **vrai** ;
    - adaptation du titre et de l'accroche ;
    - ordre des compétences selon `stack_requise`.
- **Contraintes** :
    - une page ;
    - conventions françaises ;
    - aucune donnée absente du profil maître.
- **Sortie** : un JSON `cv_adapte` conforme au schéma du CV, injecté dans un **template Typst** pour produire le PDF. La mise en page est déterministe et ne dépend pas de l'IA.
- **Édition** : un aperçu côte à côte (JSON éditable en formulaire et rendu PDF) permet les ajustements manuels, puis on régénère le PDF.
- **Templates** : un template par défaut (sobre, compatible ATS : une colonne, sans tableaux complexes). D'autres sont possibles en v2.

### F4. Génération de la lettre de motivation

- **Entrées** : profil maître, analyse de l'offre et paramètres optionnels :
    - ton : formel / neutre / direct ;
    - longueur : courte (environ 150 mots) / standard (environ 250 mots) ;
    - éléments à mettre en avant, en texte libre.
- **Structure** : accroche liée à l'entreprise, adéquation profil–poste avec 2 ou 3 preuves concrètes, motivation, conclusion et disponibilité.
- **Anti-générique** :
    - formules creuses interdites (« passionné », « dynamique », « je me permets de… ») ;
    - au moins une référence spécifique à l'offre ou à l'entreprise ;
    - chaque argument s'appuie sur un élément du profil.
- **Sorties** :
    - PDF via template Typst (en-tête, date, objet, signature) ;
    - texte brut copiable, pour les formulaires en ligne et les e-mails.
- **Option** : variante courte d'environ 80 mots pour un message LinkedIn ou un corps d'e-mail.

### F5. Audit et amélioration du CV

Il porte sur le **profil maître** ou sur un **CV PDF importé**.

**Axes analysés** :

| Axe       | Exemples de contrôles                                                             |
|-----------|-----------------------------------------------------------------------------------|
| Impact    | Puces descriptives sans résultat, absence de verbes d'action, absence de chiffres |
| Clarté    | Phrases longues, jargon interne (noms de projets non expliqués)                   |
| Cohérence | Chevauchements de dates, trous non expliqués, incohérences de niveau              |
| ATS       | Compétences noyées, intitulés non standards, mise en page problématique           |
| Langue    | Orthographe, grammaire, homogénéité des temps                                     |
| Ciblage   | Adéquation avec un type de poste cible (ex. « dev back-end Python »)              |

**Sortie** : une liste de suggestions, avec pour chacune :

- `id`, `axe`, `gravite` (critique / important / mineur) ;
- `cible` : le champ du profil concerné ;
- `avant` / `apres` : la proposition de réécriture ;
- `explication` : une phrase.

**UX** :

- vue diff par suggestion, avec les boutons **Accepter / Modifier / Rejeter** ;
- les suggestions acceptées sont appliquées au profil maître ;
- l'historique des versions du profil est conservé, avec rollback possible.

**Questions de complétion** : quand une puce manque de résultat mesurable, l'IA **pose une question** (« Combien de tickets TMA traités par mois ? ») au lieu d'inventer un chiffre.

### F6. Historique des candidatures (minimal)

- Une liste des offres analysées, avec pour chacune la date, le verdict, et les CV et lettre générés en téléchargement.
- Un statut manuel : `brouillon` / `envoyée` / `entretien` / `refus`.
- Un suivi complet façon kanban avec relances est prévu en v2.

---

## 3. Intégration Claude Code

### 3.1 Authentification

> Le projet Snake eyes dispose d'un token, si une génération coupe l'ancien, utiliser le même.

1. Installer Claude Code : `npm install -g @anthropic-ai/claude-code`
2. Générer un token longue durée lié à l'abonnement : `claude setup-token`
3. Le stocker dans `.env` sous la forme `CLAUDE_CODE_OAUTH_TOKEN=...`, sans jamais le committer (`.env` est dans `.gitignore`).

> L'usage est conforme tant qu'il reste personnel. Un déploiement de l'app pour d'autres personnes nécessiterait une clé API.

### 3.2 Appel headless

Le back-end appelle la CLI via un subprocess :

```bash
claude -p "<prompt>" \
  --output-format json \
  --model sonnet \
  --max-turns 1 \
  --disallowedTools "Bash,Edit,Write,WebFetch,WebSearch"
```

- `--output-format json` renvoie une enveloppe JSON. Le texte du modèle se trouve dans `result`, et on y lit aussi le coût et la durée.
- Les outils sont désactivés : on veut une génération pure, sans action sur le système.
- Le prompt exige une **réponse JSON stricte** conforme à un schéma, fourni dans le prompt.

**Alternative** : le SDK Python `claude-agent-sdk`, qui s'appuie sur la même CLI et la même authentification. Il est plus propre qu'un subprocess brut si le besoin grandit (streaming, gestion d'erreurs).

### 3.3 Couche `claude_client`

Un module unique encapsule les appels :

```python
def run(task: str, context: dict, schema: type[BaseModel]) -> BaseModel:
    prompt = render_prompt(task, context, schema.model_json_schema())
    raw = call_claude_cli(prompt, timeout=120)
    data = extract_json(raw["result"])        # tolère un éventuel ```json ... ```
    try:
        return schema.model_validate(data)
    except ValidationError as e:
        # 1 retry avec l'erreur renvoyée au modèle
        ...
```

- **Validation Pydantic** de chaque sortie, avec au plus 1 retry correctif.
- **Timeout** de 120 s, avec une erreur claire côté UI.
- **File d'exécution** : un seul appel Claude à la fois, pour respecter les limites d'usage de l'abonnement.
- **Journalisation** : prompt, réponse, durée et coût indicatif dans `logs/claude/`, pour le débogage.

### 3.4 Prompts

- Stockés dans `prompts/*.md`, versionnés et éditables sans toucher au code :
    - `extract_profile.md`
    - `analyze_offer.md`
    - `generate_cv.md`
    - `generate_letter.md`
    - `audit_cv.md`
- Chaque prompt contient :
    - le rôle ;
    - les règles anti-invention ;
    - le contexte (profil, offre) injecté en YAML ;
    - le schéma JSON attendu ;
    - 1 exemple court.

### 3.5 Garde-fou anti-invention

Après chaque génération, un contrôle **déterministe côté code** compare le résultat au profil maître :

- chaque entreprise, diplôme et date du CV généré doit exister dans le profil maître ;
- toute compétence absente du profil déclenche un avertissement dans l'UI ;
- tout chiffre absent du profil déclenche aussi un avertissement.

---

## 4. Architecture

```
┌────────────┐   HTTP/JSON   ┌──────────────────┐  subprocess  ┌─────────────┐
│ React (UI) │ ────────────▶ │ Django + DRF     │ ───────────▶ │ claude -p   │
└────────────┘               │  ├─ claude_client│              └─────────────┘
                             │  ├─ tasks (Huey) │
                             │  └─ pdf (Typst)  │──▶ fichiers PDF
                             └────────┬─────────┘
                                      ▼
                                   SQLite
```

| Couche       | Choix                          | Raison                                                   |
|--------------|--------------------------------|----------------------------------------------------------|
| Front        | React + Vite + TypeScript      | Stack maîtrisée                                          |
| Back         | Django + Django REST Framework | Stack maîtrisée, admin gratuit                           |
| Tâches async | Huey (backend SQLite)          | Léger, sans Redis ; les appels Claude prennent 10 à 60 s |
| Base         | SQLite                         | Mono-utilisateur, local                                  |
| PDF          | Typst (CLI)                    | Rendu propre, rapide, templates lisibles                 |
| Validation   | Pydantic                       | Schémas des sorties IA                                   |
| Lancement    | `make dev` ou Docker Compose   | La CLI Claude doit être disponible dans le conteneur     |

### Flux asynchrone

1. `POST /api/offers/{id}/generate-cv` crée un job et renvoie `job_id`.
2. Le front interroge `GET /api/jobs/{job_id}` toutes les 2 s (`pending` / `running` / `done` / `error`).
3. Quand le job est `done`, le front récupère le résultat et affiche l'aperçu.

---

## 5. Modèle de données

```
Profile        (id, version, data: JSON, created_at)          # historique des versions
Offer          (id, url?, raw_text, analysis: JSON, verdict, score, created_at)
Application    (id, offer_fk, profile_version_fk, status, created_at, updated_at)
GeneratedDoc   (id, application_fk, kind: cv|letter|letter_short,
                content: JSON, pdf_path, template, created_at)
Audit          (id, profile_version_fk, target_role?, created_at)
Suggestion     (id, audit_fk, axis, severity, target_path, before, after,
                explanation, state: pending|accepted|rejected|edited)
Job            (id, kind, status, payload, result, error, duration_ms, created_at)
```

---

## 6. API

| Méthode | Route                              | Description                                                  |
|---------|------------------------------------|--------------------------------------------------------------|
| GET/PUT | `/api/profile`                     | Lire / mettre à jour le profil maître (crée une version)     |
| POST    | `/api/profile/import`              | Upload d'un CV PDF/DOCX, puis job d'extraction               |
| GET     | `/api/profile/versions`            | Historique ; `POST .../{v}/restore`                          |
| POST    | `/api/offers`                      | Créer une offre, puis job d'analyse                          |
| GET     | `/api/offers` / `/api/offers/{id}` | Liste / détail                                               |
| POST    | `/api/offers/{id}/generate-cv`     | Job de génération du CV                                      |
| POST    | `/api/offers/{id}/generate-letter` | Job de génération de la lettre (body : ton, longueur, focus) |
| PUT     | `/api/docs/{id}`                   | Éditer le contenu, puis re-rendu du PDF                      |
| GET     | `/api/docs/{id}/pdf`               | Télécharger le PDF                                           |
| POST    | `/api/audits`                      | Lancer un audit (body : rôle cible optionnel)                |
| PATCH   | `/api/suggestions/{id}`            | Accepter / rejeter / éditer                                  |
| GET     | `/api/jobs/{id}`                   | État d'un job                                                |
| PATCH   | `/api/applications/{id}`           | Changer le statut                                            |

---

## 7. Écrans

1. **Accueil** : un bouton « Nouvelle offre » et la liste des candidatures récentes, avec verdict et statut.
2. **Profil** : un formulaire d'édition par section, les boutons « Importer un CV » et « Auditer », et l'historique des versions.
3. **Nouvelle offre** : une zone de collage, puis l'analyse avec le score, les points forts, les écarts et le verdict (badge couleur).
4. **Candidature** : deux onglets, CV et Lettre. Chacun propose l'édition à gauche, l'aperçu PDF à droite, et les boutons Télécharger / Copier le texte.
5. **Audit** : les suggestions groupées par axe et triées par gravité, une vue diff et les boutons d'action. Les questions de complétion apparaissent en tête.

---

## 8. Exigences non fonctionnelles

- **Performance** :
    - analyse d'offre en moins de 30 s ;
    - CV en moins de 60 s ;
    - lettre en moins de 45 s ;
    - rendu PDF en moins de 2 s.
- **Confidentialité** : toutes les données restent en local. Seul le contenu envoyé dans les prompts sort vers Claude.
- **Robustesse** : toute erreur de CLI (token expiré, limite d'usage atteinte, timeout) produit un message explicite dans l'UI et permet de relancer le job.
- **Qualité** :
    - tests unitaires sur `extract_json`, la validation des schémas, le garde-fou anti-invention et le rendu Typst ;
    - appels Claude mockés en CI.

---

## 9. Plan de réalisation

| Étape | Contenu                                                           | Estimation |
|-------|-------------------------------------------------------------------|------------|
| 1     | Squelette Django + React, `claude_client` + test d'appel headless | 1 j        |
| 2     | Profil maître (schéma, CRUD, versions) + import CV                | 1,5 j      |
| 3     | Analyse d'offre + verdict                                         | 1 j        |
| 4     | Génération CV + template Typst + aperçu/édition                   | 2 j        |
| 5     | Lettre de motivation (PDF + texte + variante courte)              | 1 j        |
| 6     | Audit CV + diff/accept/reject + questions de complétion           | 2 j        |
| 7     | Historique, garde-fou anti-invention, tests, finitions            | 1,5 j      |
|       | **Total MVP**                                                     | **≈ 10 j** |

---

## 10. Évolutions (v2+)

- Kanban de suivi avec rappels de relance
- Plusieurs templates de CV, en version FR et EN
- Préparation d'entretien à partir de l'offre (questions probables, pitch)
- Envoi d'e-mail de candidature (SMTP), avec relecture obligatoire
- Extension navigateur pour capturer le texte d'une offre en un clic
- Statistiques : taux de réponse par type d'offre et par verdict