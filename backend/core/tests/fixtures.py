"""Données de test partagées."""

PROFILE = {
    "identite": {"nom_complet": "Camille Martin", "email": "camille@exemple.fr", "ville": "Nantes"},
    "titre": "Développeuse back-end Python",
    "accroche": "Développeuse Python depuis 4 ans.",
    "experiences": [
        {
            "poste": "Développeuse back-end",
            "entreprise": "Exemple SAS",
            "lieu": "Nantes",
            "date_debut": "2021-03",
            "date_fin": "",
            "realisations": ["Conception de l'API de facturation utilisée par 3 applications", "Maintenance de la TMA"],
            "stack": ["Python", "Django", "PostgreSQL"],
        },
        {
            "poste": "Développeuse PHP",
            "entreprise": "Agence Web",
            "date_debut": "2019-09",
            "date_fin": "2021-02",
            "realisations": ["Sites Symfony pour 12 clients"],
            "stack": ["PHP", "Symfony"],
        },
    ],
    "formations": [{"diplome": "Master Informatique", "etablissement": "Université de Nantes", "date_debut": "2017", "date_fin": "2019"}],
    "competences": [{"nom": "Python", "categorie": "Langages"}, {"nom": "Docker", "categorie": "Outils"}],
    "projets": [{"nom": "Mue", "description": "Générateur de CV", "stack": ["React"]}],
    "langues": [{"langue": "Anglais", "niveau": "B2"}],
    "centres_interet": ["Escalade"],
}

ANALYSIS = {
    "entreprise": "Acme",
    "poste": "Développeur Python",
    "lieu": "Nantes",
    "contrat": "CDI",
    "teletravail": "",
    "stack_requise": ["Python", "Django"],
    "stack_bonus": [],
    "seniorite": "confirmé",
    "mots_cles_ats": ["Python", "Django"],
    "score_matching": 80,
    "points_forts": ["Django"],
    "ecarts": [],
    "verdict": "postuler",
    "justification": "Bonne adéquation.",
}

CV = {
    "titre": "Développeuse Python",
    "accroche": "Développeuse Python depuis 4 ans.",
    "experiences": [
        {
            "poste": "Développeuse back-end",
            "entreprise": "Exemple SAS",
            "lieu": "Nantes",
            "date_debut": "2021-03",
            "date_fin": "",
            "realisations": ["Conçu l'API de facturation utilisée par 3 applications"],
            "stack": ["Python", "Django"],
        }
    ],
    "formations": [{"diplome": "Master Informatique", "etablissement": "Université de Nantes", "date_debut": "2017", "date_fin": "2019"}],
    "competences": [{"categorie": "Back-end", "items": ["Python", "Django", "Docker"]}],
    "projets": [],
    "langues": [{"langue": "Anglais", "niveau": "B2"}],
    "centres_interet": [],
}

LETTER = {
    "objet": "Candidature au poste de développeur Python",
    "salutation": "Madame, Monsieur,",
    "paragraphes": ["Votre API de réservation m'intéresse.", "Chez Exemple SAS, j'ai conçu une API utilisée par 3 applications."],
    "formule_politesse": "Je vous prie d'agréer mes salutations distinguées.",
    "version_courte": "Bonjour, je candidate au poste de développeur Python.",
}

AUDIT = {
    "suggestions": [
        {
            "id": "s1", "axe": "impact", "gravite": "important", "cible": "experiences.0.realisations.1",
            "avant": "Maintenance de la TMA", "apres": "Assuré la maintenance corrective de l'application (TMA)",
            "explication": "Verbe d'action.",
        },
        {"id": "s2", "axe": "ats", "gravite": "mineur", "cible": "chemin.inexistant", "avant": "", "apres": "", "explication": "Global."},
        {"id": "s3", "axe": "ciblage", "gravite": "mineur", "cible": "projets", "avant": "", "apres": "Ajouter un projet", "explication": "Liste."},
        {"id": "s4", "axe": "clarte", "gravite": "mineur", "cible": "accroche", "avant": "", "apres": "", "explication": "Sans réécriture."},
    ],
    "questions": [{"id": "q1", "cible": "experiences.0.realisations.1", "question": "Combien de tickets par mois ?"}],
}

OFFER_TEXT = "Acme recrute un développeur Python / Django confirmé en CDI à Nantes. " * 4

REVISION = {
    "profil": {
        **PROFILE,
        "experiences": [
            {**PROFILE["experiences"][0], "realisations": [
                "Conçu l'API de facturation utilisée par 3 applications",
                "Traité 40 tickets de TMA par mois",
                "Réduit le délai de résolution de 5 jours",
            ]},
            PROFILE["experiences"][1],
        ],
    },
    "changements": ["Exemple SAS, puce 2 : ajout du volume de tickets."],
}
