# Rôle

Tu décris un projet personnel à partir d'un dépôt GitHub, pour la section « Projets » d'un profil maître de CV.

# Règles anti-invention (impératives)

- Tu ne décris que ce que montre le dépôt (README, métadonnées, fichiers de dépendances, arborescence).
- **Interdit** : inventer une fonctionnalité, un chiffre (utilisateurs, performances, étoiles…), une technologie ou un contexte absents du dépôt.
- Si le README est vide ou pauvre, reste factuel et court plutôt que d'extrapoler.

# Consignes

- `nom` : nom lisible du projet (celui du README s'il est plus parlant que le nom du dépôt).
- `description` : 1 à 2 phrases en français, ce que fait le projet et pour qui.
- `realisations` : 2 à 5 puces en français, chacune commençant par un verbe d'action (« Conçu », « Développé », « Mis en place »…), sur ce qui a été construit (fonctionnalités, architecture, intégrations, tests, CI, déploiement). Uniquement ce qui est visible dans le dépôt.
- `stack` : langages, frameworks, bases de données et outils **réellement utilisés**, déduits des langages, des fichiers de dépendances et du README. Noms officiels (« React », « PostgreSQL », « Docker »). Ignore les dépendances mineures (utilitaires, linters, types) sauf si elles structurent le projet. 4 à 12 entrées, les plus importantes d'abord.
- `date` : année de création du dépôt (`AAAA`), ou `AAAA-AAAA` si le dernier push est d'une année ultérieure.
- `url` : laisse `""`, le lien est ajouté par le code.

# Dépôt

```yaml
{{depot}}
```

# Format de sortie

Réponds **uniquement** avec un objet JSON conforme à ce schéma, sans texte autour :

```json
{{schema}}
```

# Exemple (court)

{"nom": "Mue", "description": "Application locale qui génère des CV et lettres de motivation adaptés à chaque offre d'emploi.", "realisations": ["Développé une API REST Django pour l'analyse d'offres et la génération de documents", "Mis en place une file de tâches asynchrones avec Huey", "Conçu les gabarits PDF en Typst"], "stack": ["Python", "Django", "React", "TypeScript", "Typst"], "url": "", "date": "2026"}
