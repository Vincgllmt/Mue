import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { CommaList, Field, ObjectList, Row, StringList } from "../components/forms";
import { JobStatus, useJob } from "../components/job";
import { formatDateTime } from "../components/ui";
import type { ProfileData, ProfileResponse, ProfileVersion } from "../types";

const SECTIONS = [
  ["identite", "Identité"],
  ["experiences", "Expériences"],
  ["formations", "Formations"],
  ["competences", "Compétences"],
  ["projets", "Projets"],
  ["divers", "Langues et intérêts"],
  ["versions", "Historique"],
] as const;

export default function ProfilePage() {
  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [draft, setDraft] = useState<ProfileData | null>(null);
  const [imported, setImported] = useState(false);
  const [versions, setVersions] = useState<ProfileVersion[]>([]);
  const [message, setMessage] = useState<{ tone: string; text: string } | null>(null);
  const [saving, setSaving] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const load = async () => {
    const p = await api.getProfile();
    setProfile(p);
    setDraft(p.data);
    setImported(false);
    setVersions(await api.versions());
  };
  useEffect(() => {
    load().catch((e) => setMessage({ tone: "error", text: e.message }));
  }, []);

  const importJob = useJob((job) => {
    setDraft(job.result!.profile as ProfileData);
    setImported(true);
    setMessage({ tone: "warning", text: "Extraction terminée : vérifie chaque section, puis clique sur « Valider l'import »." });
  });

  if (!draft || !profile) return message ? <div className={`alert ${message.tone}`}>{message.text}</div> : <p className="muted">Chargement…</p>;

  const dirty = JSON.stringify(draft) !== JSON.stringify(profile.data);
  const set = (patch: Partial<ProfileData>) => setDraft({ ...draft, ...patch });
  const setId = (patch: Partial<ProfileData["identite"]>) => set({ identite: { ...draft.identite, ...patch } });

  const save = async () => {
    setSaving(true);
    try {
      const saved = await api.saveProfile(draft, imported ? "Import de CV" : undefined);
      setProfile(saved);
      setDraft(saved.data);
      setImported(false);
      setVersions(await api.versions());
      setMessage({ tone: "success", text: `Profil enregistré (version ${saved.version}).` });
    } catch (e) {
      setMessage({ tone: "error", text: (e as Error).message });
    } finally {
      setSaving(false);
    }
  };

  const restore = async (v: number) => {
    if (dirty && !window.confirm("Des modifications non enregistrées seront perdues. Continuer ?")) return;
    const restored = await api.restoreVersion(v);
    await load();
    setMessage({ tone: "success", text: `Version ${v} restaurée (nouvelle version ${restored.version}).` });
  };

  return (
    <section className="with-sidebar">
      <aside className="sidebar">
        {SECTIONS.map(([id, label]) => <a key={id} href={`#${id}`}>{label}</a>)}
      </aside>
      <div>
        <div className="page-head">
          <div>
            <h1>Profil maître</h1>
            <p className="muted">
              Source de vérité unique : sois exhaustif, l'IA fait la sélection.{" "}
              {profile.version ? `Version ${profile.version} — ${profile.note}` : "Aucune version enregistrée."}
              {" "}Aussi éditable à la main dans <code>data/profile.yaml</code>.
            </p>
          </div>
          <div className="head-actions">
            <input ref={fileInput} type="file" accept=".pdf,.docx" hidden
                   onChange={(e) => {
                     const f = e.target.files?.[0];
                     e.target.value = "";
                     if (f) importJob.start(() => api.importCv(f));
                   }} />
            <button disabled={importJob.running} onClick={() => fileInput.current?.click()}>Importer un CV</button>
            <Link className="button" to="/audit">Auditer</Link>
          </div>
        </div>

        {profile.yaml_error && <div className="alert error">{profile.yaml_error}</div>}
        <JobStatus job={importJob.job} error={importJob.error} onRetry={importJob.retry} />
        {message && <div className={`alert ${message.tone}`}>{message.text}</div>}

        <div className="toolbar sticky">
          <button className="primary" disabled={(!dirty && !imported) || saving} onClick={save}>
            {imported ? "Valider l'import" : "Enregistrer (nouvelle version)"}
          </button>
          {dirty && <button onClick={() => { setDraft(profile.data); setImported(false); }}>Annuler les modifications</button>}
          {dirty && <span className="muted">Modifications non enregistrées</span>}
        </div>

        <h2 id="identite">Identité</h2>
        <Row>
          <Field label="Nom complet" value={draft.identite.nom_complet} onChange={(nom_complet) => setId({ nom_complet })} />
          <Field label="Ville" value={draft.identite.ville} onChange={(ville) => setId({ ville })} />
        </Row>
        <Row>
          <Field label="E-mail" value={draft.identite.email} onChange={(email) => setId({ email })} />
          <Field label="Téléphone" value={draft.identite.telephone} onChange={(telephone) => setId({ telephone })} />
        </Row>
        <Row>
          <Field label="LinkedIn" value={draft.identite.linkedin} onChange={(linkedin) => setId({ linkedin })} />
          <Field label="GitHub" value={draft.identite.github} onChange={(github) => setId({ github })} />
          <Field label="Site" value={draft.identite.site} onChange={(site) => setId({ site })} />
        </Row>
        <Field label="Titre" value={draft.titre} onChange={(titre) => set({ titre })} />
        <Field label="Accroche" value={draft.accroche} onChange={(accroche) => set({ accroche })} multiline />

        <h2 id="experiences">Expériences</h2>
        <ObjectList
          items={draft.experiences}
          onChange={(experiences) => set({ experiences })}
          title={(e) => `${e.poste} — ${e.entreprise} (${e.date_debut || "?"} → ${e.date_fin || "en cours"})`}
          addLabel="+ Ajouter une expérience"
          empty={() => ({ poste: "", entreprise: "", lieu: "", date_debut: "", date_fin: "", contexte: "", realisations: [], stack: [] })}
          render={(e, up) => (
            <>
              <Row>
                <Field label="Poste" value={e.poste} onChange={(poste) => up({ poste })} />
                <Field label="Entreprise" value={e.entreprise} onChange={(entreprise) => up({ entreprise })} />
                <Field label="Lieu" value={e.lieu} onChange={(lieu) => up({ lieu })} />
              </Row>
              <Row>
                <Field label="Début" value={e.date_debut} onChange={(date_debut) => up({ date_debut })} placeholder="AAAA-MM" />
                <Field label="Fin" value={e.date_fin} onChange={(date_fin) => up({ date_fin })} placeholder="vide = en cours" />
              </Row>
              <Field label="Contexte" value={e.contexte} onChange={(contexte) => up({ contexte })} multiline rows={2}
                     hint="Client, équipe, produit, enjeux : tout ce qui aide l'IA à comprendre." />
              <StringList label="Réalisations détaillées" items={e.realisations} onChange={(realisations) => up({ realisations })} multiline />
              <CommaList label="Stack" items={e.stack} onChange={(stack) => up({ stack })} />
            </>
          )}
        />

        <h2 id="formations">Formations</h2>
        <ObjectList
          items={draft.formations}
          onChange={(formations) => set({ formations })}
          title={(f) => `${f.diplome} — ${f.etablissement}`}
          addLabel="+ Ajouter une formation"
          empty={() => ({ diplome: "", etablissement: "", lieu: "", date_debut: "", date_fin: "", details: "" })}
          render={(f, up) => (
            <>
              <Row>
                <Field label="Diplôme" value={f.diplome} onChange={(diplome) => up({ diplome })} />
                <Field label="Établissement" value={f.etablissement} onChange={(etablissement) => up({ etablissement })} />
                <Field label="Lieu" value={f.lieu} onChange={(lieu) => up({ lieu })} />
              </Row>
              <Row>
                <Field label="Début" value={f.date_debut} onChange={(date_debut) => up({ date_debut })} />
                <Field label="Fin" value={f.date_fin} onChange={(date_fin) => up({ date_fin })} />
              </Row>
              <Field label="Détails" value={f.details} onChange={(details) => up({ details })} multiline rows={2} />
            </>
          )}
        />

        <h2 id="competences">Compétences</h2>
        <table className="table compact">
          <thead><tr><th>Compétence</th><th>Catégorie</th><th>Niveau</th><th /></tr></thead>
          <tbody>
            {draft.competences.map((c, i) => {
              const up = (patch: Partial<typeof c>) =>
                set({ competences: draft.competences.map((x, j) => (j === i ? { ...x, ...patch } : x)) });
              return (
                <tr key={i}>
                  <td><input value={c.nom} onChange={(e) => up({ nom: e.target.value })} /></td>
                  <td><input value={c.categorie} onChange={(e) => up({ categorie: e.target.value })} list="categories" /></td>
                  <td><input value={c.niveau} onChange={(e) => up({ niveau: e.target.value })} placeholder="ex. avancé" /></td>
                  <td><button className="icon" onClick={() => set({ competences: draft.competences.filter((_, j) => j !== i) })}>✕</button></td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <datalist id="categories">
          {[...new Set(draft.competences.map((c) => c.categorie).filter(Boolean))].map((c) => <option key={c} value={c} />)}
        </datalist>
        <button className="link" onClick={() => set({ competences: [...draft.competences, { nom: "", categorie: "", niveau: "" }] })}>
          + Ajouter une compétence
        </button>

        <h2 id="projets">Projets</h2>
        <ObjectList
          items={draft.projets}
          onChange={(projets) => set({ projets })}
          title={(p) => p.nom}
          addLabel="+ Ajouter un projet"
          empty={() => ({ nom: "", description: "", realisations: [], stack: [], url: "", date: "" })}
          render={(p, up) => (
            <>
              <Row>
                <Field label="Nom" value={p.nom} onChange={(nom) => up({ nom })} />
                <Field label="Date" value={p.date} onChange={(date) => up({ date })} />
                <Field label="URL" value={p.url} onChange={(url) => up({ url })} />
              </Row>
              <Field label="Description" value={p.description} onChange={(description) => up({ description })} multiline rows={2} />
              <StringList label="Réalisations" items={p.realisations} onChange={(realisations) => up({ realisations })} multiline />
              <CommaList label="Stack" items={p.stack} onChange={(stack) => up({ stack })} />
            </>
          )}
        />

        <h2 id="divers">Langues et centres d'intérêt</h2>
        <ObjectList
          items={draft.langues}
          onChange={(langues) => set({ langues })}
          title={(l) => `${l.langue} ${l.niveau ? `(${l.niveau})` : ""}`}
          addLabel="+ Ajouter une langue"
          empty={() => ({ langue: "", niveau: "" })}
          render={(l, up) => (
            <Row>
              <Field label="Langue" value={l.langue} onChange={(langue) => up({ langue })} />
              <Field label="Niveau" value={l.niveau} onChange={(niveau) => up({ niveau })} placeholder="ex. C1, courant" />
            </Row>
          )}
        />
        <StringList label="Centres d'intérêt" items={draft.centres_interet} onChange={(centres_interet) => set({ centres_interet })} />

        <h2 id="versions">Historique des versions</h2>
        {versions.length === 0 && <p className="muted">Aucune version.</p>}
        <table className="table compact">
          <tbody>
            {versions.map((v) => (
              <tr key={v.version}>
                <td><strong>v{v.version}</strong></td>
                <td>{v.note}</td>
                <td className="muted nowrap">{formatDateTime(v.created_at)}</td>
                <td>
                  {v.version === profile.version
                    ? <span className="badge gray">Actuelle</span>
                    : <button className="small" onClick={() => restore(v.version)}>Restaurer</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
