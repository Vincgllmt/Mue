import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { Diff } from "../components/Diff";
import { Field } from "../components/forms";
import { JobStatus, useJob } from "../components/job";
import { formatDateTime, Warnings } from "../components/ui";
import type { Audit, Suggestion } from "../types";

const AXES: Record<string, string> = {
  impact: "Impact",
  clarte: "Clarté",
  coherence: "Cohérence",
  ats: "ATS",
  langue: "Langue",
  ciblage: "Ciblage",
};
const SEVERITY_ORDER = { critique: 0, important: 1, mineur: 2 };
const STATE_LABELS = { pending: "", accepted: "Acceptée", rejected: "Rejetée", edited: "Modifiée et appliquée" };

export default function AuditPage() {
  const params = useParams();
  return params.id ? <AuditDetail id={Number(params.id)} /> : <AuditLauncher />;
}

function AuditLauncher() {
  const [role, setRole] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [audits, setAudits] = useState<Audit[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    api.audits().then(setAudits).catch((e) => setError(e.message));
  }, []);

  const launch = async () => {
    setBusy(true);
    setError("");
    try {
      const { audit } = await api.startAudit(role, file);
      navigate(`/audit/${audit.id}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
    }
  };

  return (
    <section className="narrow">
      <h1>Audit du CV</h1>
      <p className="muted">
        Analyse impact, clarté, cohérence, ATS, langue et ciblage. Les suggestions acceptées sont appliquées au profil maître
        (une nouvelle version est créée à chaque fois).
      </p>
      <div className="card">
        <Field label="Poste cible (optionnel)" value={role} onChange={setRole} placeholder="ex. dev back-end Python" />
        <label className="field">
          <span className="field-label">Auditer un CV PDF/DOCX plutôt que le profil maître (optionnel)</span>
          <input type="file" accept=".pdf,.docx" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        </label>
        {error && <div className="alert error">{error}</div>}
        <button className="primary" disabled={busy} onClick={launch}>
          {busy ? "Lancement…" : file ? "Auditer ce fichier" : "Auditer le profil maître"}
        </button>
      </div>

      {audits.length > 0 && (
        <>
          <h2>Audits précédents</h2>
          <table className="table compact">
            <tbody>
              {audits.map((a) => {
                const pending = a.suggestions.filter((s) => s.state === "pending").length;
                return (
                  <tr key={a.id}>
                    <td><Link to={`/audit/${a.id}`}>Audit #{a.id}</Link></td>
                    <td>{a.source === "file" ? "CV importé" : `Profil v${a.profile_version ?? "?"}`}</td>
                    <td>{a.target_role || <span className="muted">sans cible</span>}</td>
                    <td>{a.job?.status === "error" ? <span className="error-text">échec</span> : `${a.suggestions.length} suggestions, ${pending} en attente`}</td>
                    <td className="muted nowrap">{formatDateTime(a.created_at)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}

function AuditDetail({ id }: { id: number }) {
  const [audit, setAudit] = useState<Audit | null>(null);
  const [error, setError] = useState("");
  // Réponses en cours de saisie, envoyées à la sortie du champ ou avant la révision.
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const job = useJob(() => load());
  const revisionJob = useJob(() => load());

  const load = () => api.audit(id).then((a) => { setAudit(a); return a; }).catch((e) => { setError(e.message); return null; });
  useEffect(() => {
    load().then((a) => {
      if (a?.job && a.job.status !== "done") job.follow(a.job.id);
      if (a?.revision_job && a.revision_job.status !== "done") revisionJob.follow(a.revision_job.id);
    });
  }, [id]);

  if (error) return <div className="alert error">{error}</div>;
  if (!audit) return <p className="muted">Chargement…</p>;

  const update = (s: Suggestion) => setAudit((a) => a && { ...a, suggestions: a.suggestions.map((x) => (x.id === s.id ? s : x)) });
  const unsaved = audit.suggestions.filter((s) => s.id in drafts && drafts[s.id].trim() !== s.response);
  const saveResponse = async (s: Suggestion) => {
    update(await api.respondSuggestion(s.id, drafts[s.id]));
    setDrafts(({ [s.id]: _, ...rest }) => rest);
  };
  const responseProps = (s: Suggestion): ResponseProps => ({
    value: drafts[s.id] ?? s.response,
    onChange: (v) => setDrafts((d) => ({ ...d, [s.id]: v })),
    onSave: () => (unsaved.some((u) => u.id === s.id) ? saveResponse(s) : Promise.resolve()),
  });
  const revise = () => revisionJob.start(async () => {
    await Promise.all(unsaved.map(saveResponse));
    return api.reviseAudit(audit.id);
  });
  const questions = audit.suggestions.filter((s) => s.kind === "question");
  const suggestions = audit.suggestions.filter((s) => s.kind === "suggestion");
  const byAxis = Object.keys(AXES)
    .map((axis) => ({
      axis,
      items: suggestions.filter((s) => s.axis === axis).sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]),
    }))
    .filter((g) => g.items.length);
  const pending = audit.suggestions.filter((s) => s.state === "pending").length;

  return (
    <section className="narrow wide">
      <Link to="/audit" className="muted">← Audits</Link>
      <h1>Audit #{audit.id}</h1>
      <p className="muted">
        {audit.source === "file" ? "CV importé (les suggestions sont à reporter à la main)" : `Profil maître v${audit.profile_version}`}
        {audit.target_role && ` · cible : ${audit.target_role}`} · {pending} en attente sur {audit.suggestions.length}
      </p>
      <JobStatus job={job.job} error={job.error} onRetry={job.retry} />

      {questions.length > 0 && (
        <>
          <h2>Questions de complétion</h2>
          <p className="muted">L'IA ne devine pas les chiffres : réponds en réécrivant la puce avec le résultat réel.</p>
          {questions.map((q) => (
            <QuestionCard key={q.id} q={q} canApply={audit.source === "profile"} onChange={update} response={responseProps(q)} />
          ))}
        </>
      )}

      {byAxis.map(({ axis, items }) => (
        <div key={axis}>
          <h2>{AXES[axis]} <span className="count">{items.length}</span></h2>
          {items.map((s) => (
            <SuggestionCard key={s.id} s={s} canApply={audit.source === "profile"} onChange={update} response={responseProps(s)} />
          ))}
        </div>
      ))}

      {audit.suggestions.length > 0 && (
        <Revision audit={audit} job={revisionJob} onRevise={revise} onApplied={setAudit} />
      )}
    </section>
  );
}

function useSuggestionAction(s: Suggestion, onChange: (s: Suggestion) => void) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const act = async (state: Suggestion["state"], after?: string) => {
    setBusy(true);
    setError("");
    try {
      onChange(await api.updateSuggestion(s.id, state, after));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return { act, error, busy };
}

type ResponseProps = { value: string; onChange: (v: string) => void; onSave: () => Promise<unknown> };

function ResponseBox({ value, onChange, onSave, label }: ResponseProps & { label: string }) {
  const [error, setError] = useState("");
  const save = () => onSave().then(() => setError(""), (e) => setError((e as Error).message));
  return (
    <label className="field response">
      <span className="field-label">{label}</span>
      <textarea rows={2} value={value} onChange={(e) => onChange(e.target.value)} onBlur={save}
        placeholder="Précision, chiffre réel, contexte, raison du refus… (pris en compte par le CV révisé)" />
      {error && <span className="error-text">{error}</span>}
    </label>
  );
}

function Header({ s }: { s: Suggestion }) {
  return (
    <div className="suggestion-head">
      <span className={`badge sev-${s.severity}`}>{s.severity}</span>
      {s.target_path ? <code>{s.target_path}</code> : <span className="muted">remarque globale</span>}
      {s.state !== "pending" && (
        <span className="badge gray">
          {STATE_LABELS[s.state]}{s.applied_version ? ` → profil v${s.applied_version}` : ""}
        </span>
      )}
    </div>
  );
}

type CardProps = { canApply: boolean; onChange: (s: Suggestion) => void; response: ResponseProps };

function SuggestionCard({ s, canApply, onChange, response }: CardProps & { s: Suggestion }) {
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(s.after);
  const { act, error, busy } = useSuggestionAction(s, onChange);
  const done = s.state !== "pending";

  return (
    <div className={`card suggestion ${done ? "done" : ""}`}>
      <Header s={s} />
      {s.explanation && <p>{s.explanation}</p>}
      {(s.before || s.after) && <Diff before={s.before} after={s.after} />}
      {editing && <textarea rows={3} value={text} onChange={(e) => setText(e.target.value)} />}
      <ResponseBox {...response} label="Ta réponse (optionnel)" />
      {error && <div className="alert error">{error}</div>}
      {!done && (
        <div className="toolbar">
          {editing ? (
            <>
              <button className="primary" disabled={busy} onClick={() => act("edited", text)}>Appliquer ma version</button>
              <button onClick={() => setEditing(false)}>Annuler</button>
            </>
          ) : (
            <>
              <button className="primary" disabled={busy} onClick={() => act("accepted")}>
                {canApply && s.target_path && s.after ? "Accepter" : "Marquer comme traitée"}
              </button>
              {canApply && s.target_path && <button disabled={busy} onClick={() => setEditing(true)}>Modifier</button>}
              <button disabled={busy} onClick={() => act("rejected")}>Rejeter</button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function QuestionCard({ q, canApply, onChange, response }: CardProps & { q: Suggestion }) {
  const [text, setText] = useState(q.after || q.before);
  const { act, error, busy } = useSuggestionAction(q, onChange);
  const done = q.state !== "pending";
  return (
    <div className={`card suggestion question ${done ? "done" : ""}`}>
      <Header s={q} />
      <p className="question-text">❓ {q.question}</p>
      {q.before && <p className="muted">Actuellement : « {q.before} »</p>}
      <ResponseBox {...response} label="Ta réponse" />
      {!done && (
        <>
          {canApply && q.target_path && (
            <textarea rows={2} value={text} onChange={(e) => setText(e.target.value)} />
          )}
          {error && <div className="alert error">{error}</div>}
          <div className="toolbar">
            {canApply && q.target_path && (
              <button className="primary" disabled={busy || text === q.before} onClick={() => act("edited", text)}>
                Appliquer au profil
              </button>
            )}
            <button disabled={busy} onClick={() => act("rejected")}>Ignorer</button>
          </div>
        </>
      )}
      {done && q.state === "edited" && <Diff before={q.before} after={q.after} />}
    </div>
  );
}

function Revision({ audit, job, onRevise, onApplied }: {
  audit: Audit;
  job: ReturnType<typeof useJob>;
  onRevise: () => void;
  onApplied: (a: Audit) => void;
}) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const rev = audit.revision;
  const answered = audit.suggestions.filter((s) => s.response).length;

  const apply = async () => {
    setBusy(true);
    setError("");
    try {
      onApplied(await api.applyRevision(audit.id));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="revision">
      <h2>CV révisé</h2>
      <p className="muted">
        L'IA réécrit le CV complet à partir des remarques et de tes réponses ({answered} sur {audit.suggestions.length}).
        Les remarques rejetées ne sont pas appliquées, mais ta réponse est prise en compte. Rien n'est enregistré dans le
        profil avant validation.
      </p>
      <div className="toolbar">
        <button className="primary" disabled={job.running} onClick={onRevise}>
          {rev ? "Régénérer le CV révisé" : "Générer le CV révisé avec mes réponses"}
        </button>
      </div>
      <JobStatus job={job.job} error={job.error} onRetry={job.retry} />

      {rev && !job.running && (
        <>
          {rev.changements.length > 0 && <ul>{rev.changements.map((c, i) => <li key={i}>{c}</li>)}</ul>}
          <Warnings warnings={rev.warnings} />
          {error && <div className="alert error">{error}</div>}
          <div className="toolbar">
            {rev.applied_version ? (
              <span className="badge gray">Appliqué → profil v{rev.applied_version}</span>
            ) : (
              <button className="primary" disabled={busy} onClick={apply}>
                {audit.source === "file" ? "Remplacer le profil maître par ce CV" : "Appliquer au profil maître"}
              </button>
            )}
            {audit.revision_pdf_url && (
              <a className="button" href={`/api/audits/${audit.id}/revision/pdf?download=1`}>Télécharger le PDF</a>
            )}
          </div>
          {audit.revision_pdf_url && <iframe title="CV révisé" src={audit.revision_pdf_url} />}
        </>
      )}
    </div>
  );
}
