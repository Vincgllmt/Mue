// Miroir des schémas Pydantic du back-end (core/schemas.py).

export interface Identite {
  nom_complet: string;
  email: string;
  telephone: string;
  ville: string;
  linkedin: string;
  github: string;
  site: string;
}

export interface Experience {
  poste: string;
  entreprise: string;
  lieu: string;
  date_debut: string;
  date_fin: string;
  contexte: string;
  realisations: string[];
  stack: string[];
}

export interface Formation {
  diplome: string;
  etablissement: string;
  lieu: string;
  date_debut: string;
  date_fin: string;
  details: string;
}

export interface Competence {
  nom: string;
  categorie: string;
  niveau: string;
}

export interface Projet {
  nom: string;
  description: string;
  realisations: string[];
  stack: string[];
  url: string;
  date: string;
}

export interface Langue {
  langue: string;
  niveau: string;
}

export interface ProfileData {
  identite: Identite;
  titre: string;
  accroche: string;
  experiences: Experience[];
  formations: Formation[];
  competences: Competence[];
  projets: Projet[];
  langues: Langue[];
  centres_interet: string[];
}

export interface ProfileResponse {
  version: number | null;
  note: string;
  created_at: string | null;
  data: ProfileData;
  yaml_error: string;
}

export interface ProfileVersion {
  version: number;
  note: string;
  created_at: string;
}

export type Verdict = "postuler" | "postuler_avec_reserve" | "ne_pas_postuler";

export interface OfferAnalysis {
  entreprise: string;
  poste: string;
  lieu: string;
  contrat: string;
  teletravail: string;
  stack_requise: string[];
  stack_bonus: string[];
  seniorite: string;
  mots_cles_ats: string[];
  score_matching: number;
  points_forts: string[];
  ecarts: string[];
  verdict: Verdict;
  justification: string;
}

export type JobStatus = "pending" | "running" | "done" | "error";

export interface JobRef {
  id: number;
  status: JobStatus;
  error: string;
}

export interface Job extends JobRef {
  kind: string;
  payload: Record<string, unknown>;
  result: Record<string, any> | null;
  duration_ms: number | null;
  cost_usd: number | null;
}

export interface GuardWarning {
  niveau: "erreur" | "avertissement";
  champ: string;
  message: string;
}

export type DocKind = "cv" | "letter" | "letter_short";

export interface GeneratedDoc<C = any> {
  id: number;
  application: number;
  kind: DocKind;
  content: C;
  warnings: GuardWarning[];
  template: string;
  pdf_url: string | null;
  text: string | null;
  created_at: string;
  updated_at: string;
}

export type ApplicationStatus = "brouillon" | "envoyee" | "entretien" | "refus";

export interface Application {
  id: number;
  status: ApplicationStatus;
  profile_version: number | null;
  docs: GeneratedDoc[];
  created_at: string;
  updated_at: string;
}

export interface Offer {
  id: number;
  url: string;
  raw_text?: string;
  analysis: OfferAnalysis | null;
  verdict: Verdict | "";
  score: number | null;
  created_at: string;
  application: Application | null;
  analysis_job: JobRef | null;
}

export interface CvExperience {
  poste: string;
  entreprise: string;
  lieu: string;
  date_debut: string;
  date_fin: string;
  realisations: string[];
  stack: string[];
}

export interface CvContent {
  identite: Identite;
  titre: string;
  accroche: string;
  experiences: CvExperience[];
  formations: { diplome: string; etablissement: string; date_debut: string; date_fin: string; details: string }[];
  competences: { categorie: string; items: string[] }[];
  projets: { nom: string; description: string; stack: string[] }[];
  langues: Langue[];
  centres_interet: string[];
}

export interface LetterContent {
  identite: Identite;
  destinataire: string;
  lieu_date: string;
  objet: string;
  salutation: string;
  paragraphes: string[];
  formule_politesse: string;
}

export interface Suggestion {
  id: number;
  audit: number;
  kind: "suggestion" | "question";
  axis: string;
  severity: "critique" | "important" | "mineur";
  target_path: string;
  before: string;
  after: string;
  question: string;
  explanation: string;
  state: "pending" | "accepted" | "rejected" | "edited";
  applied_version: number | null;
}

export interface Audit {
  id: number;
  profile_version: number | null;
  target_role: string;
  source: "profile" | "file";
  created_at: string;
  suggestions: Suggestion[];
  job: JobRef | null;
}
