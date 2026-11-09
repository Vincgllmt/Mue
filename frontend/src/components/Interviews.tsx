import { useEffect, useState } from "react";
import { api } from "../api";
import type { Interview, InterviewFeeling, InterviewKind, InterviewPrep, InterviewQuestion, Offer } from "../types";
import { Field } from "./forms";
import { JobStatus, useJob } from "./job";
import { CopyButton, formatDateTime } from "./ui";

export const INTERVIEW_KINDS: Record<InterviewKind, string> = {
  rh: "RH",
  technique: "Technique",
  manager: "Manager",
  culture: "Culture fit",
};

const FEELINGS: Record<InterviewFeeling, string> = { "": "—", bien: "Bien passé", mitige: "Mitigé", mal: "Mal passé" };

const CATEGORIES: Record<InterviewQuestion["categorie"], string> = {
  parcours: "Parcours",
  motivation: "Motivation",
  technique: "Technique",
  comportementale: "Comportementale",
  ecart: "Écarts",
};

/** ISO → valeur d'un `<input type="datetime-local">` (heure locale). */
function toLocalInput(iso: string | null) {
  if (!iso) return "";
  const d = new Date(iso);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

const fromLocalInput = (value: string) => (value ? new Date(value).toISOString() : null);

const interviewLabel = (i: Interview) =>
  [INTERVIEW_KINDS[i.kind], i.scheduled_at ? formatDateTime(i.scheduled_at) : "date non fixée"].join(" — ");

export function InterviewsTab({ offer, reload }: { offer: Offer; reload: () => Promise<Offer | null> }) {
  const [interviews, setInterviews] = useState<Interview[] | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");

  const refresh = () =>
    api.interviews(offer.id).then(setInterviews).catch((e) => setError((e as Error).message));

  useEffect(() => { refresh(); }, [offer.id]);

  if (error) return <div className="alert error">{error}</div>;
  if (!interviews) return <p className="muted">Chargement…</p>;

  const selected = interviews.find((i) => i.id === selectedId) ?? interviews[0] ?? null;
  const showForm = creating || !selected;

  return (
    <div>
      {interviews.length > 0 && (
        <div className="toolbar">
          <select value={selected?.id ?? ""} onChange={(e) => { setSelectedId(Number(e.target.value)); setCreating(false); }}>
            {interviews.map((i) => <option key={i.id} value={i.id}>{interviewLabel(i)}</option>)}
          </select>
          {!creating && <button onClick={() => setCreating(true)}>+ Nouvel entretien</button>}
        </div>
      )}
      {showForm && (
        <NewInterview
          offer={offer}
          onCancel={interviews.length ? () => setCreating(false) : undefined}
          onCreated={async (interview) => {
            setSelectedId(interview.id);
            setCreating(false);
            await Promise.all([refresh(), reload()]); // le statut de la candidature a pu passer à « entretien »
          }}
        />
      )}
      {!showForm && selected && (
        <InterviewDetail
          key={selected.id}
          interview={selected}
          onChanged={refresh}
          onDeleted={async () => { setSelectedId(null); await refresh(); }}
        />
      )}
    </div>
  );
}

function NewInterview({ offer, onCreated, onCancel }: {
  offer: Offer;
  onCreated: (i: Interview) => Promise<void>;
  onCancel?: () => void;
}) {
  const [kind, setKind] = useState<InterviewKind>("rh");
  const [date, setDate] = useState("");
  const [context, setContext] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  const create = async () => {
    setSending(true);
    setError("");
    try {
      const { interview } = await api.createInterview(offer.id, { kind, scheduled_at: fromLocalInput(date), context });
      await onCreated(interview);
    } catch (e) {
      setError((e as Error).message);
      setSending(false);
    }
  };

  return (
    <div className="card options">
      <label className="field inline">
        <span className="field-label">Type d'entretien</span>
        <select value={kind} onChange={(e) => setKind(e.target.value as InterviewKind)}>
          {Object.entries(INTERVIEW_KINDS).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
        </select>
      </label>
      <label className="field inline">
        <span className="field-label">Date et heure (optionnel)</span>
        <input type="datetime-local" value={date} onChange={(e) => setDate(e.target.value)} />
      </label>
      <Field label="Ce que tu sais déjà (optionnel)" value={context} onChange={setContext} multiline rows={2}
             placeholder="ex. visio de 45 min avec le CTO, live coding annoncé, deuxième tour…" />
      {error && <div className="alert error">{error}</div>}
      <div className="toolbar">
        <button className="primary" disabled={sending} onClick={create}>Préparer l'entretien</button>
        {onCancel && <button onClick={onCancel}>Annuler</button>}
      </div>
    </div>
  );
}

function InterviewDetail({ interview, onChanged, onDeleted }: {
  interview: Interview;
  onChanged: () => Promise<unknown>;
  onDeleted: () => Promise<unknown>;
}) {
  const gen = useJob(() => onChanged());

  useEffect(() => {
    const job = interview.job;
    if (job && (job.status === "pending" || job.status === "running" || job.status === "error")) gen.follow(job.id);
  }, [interview.id]);

  const remove = async () => {
    if (!window.confirm("Supprimer cet entretien, sa préparation et son débrief ?")) return;
    await api.deleteInterview(interview.id);
    await onDeleted();
  };

  return (
    <div>
      <div className="toolbar">
        <button disabled={gen.running} onClick={() => gen.start(() => api.prepareInterview(interview.id))}>
          {interview.prep ? "Régénérer la fiche" : "Générer la fiche"}
        </button>
        <button className="danger small" onClick={remove}>Supprimer</button>
      </div>
      <JobStatus job={gen.job} error={gen.error} onRetry={gen.retry} />
      <div className="interview">
        <div className="interview-prep">
          {interview.prep ? <PrepView prep={interview.prep} /> : !gen.running && <p className="muted">Pas encore de fiche.</p>}
        </div>
        <Debrief interview={interview} onSaved={onChanged} />
      </div>
    </div>
  );
}

/** Met en évidence les « [à compléter] » laissés par l'IA quand le profil ne dit rien. */
function WithBlanks({ text }: { text: string }) {
  return (
    <>
      {text.split(/(\[[^\]]+\])/).map((part, i) => (/^\[.*\]$/.test(part) ? <mark key={i}>{part}</mark> : part))}
    </>
  );
}

function PrepView({ prep }: { prep: InterviewPrep }) {
  const words = prep.pitch.trim().split(/\s+/).filter(Boolean).length;
  const groups = (Object.keys(CATEGORIES) as InterviewQuestion["categorie"][])
    .map((cat) => [cat, prep.questions.filter((q) => q.categorie === cat)] as const)
    .filter(([, qs]) => qs.length > 0);

  return (
    <>
      <div className="card">
        <div className="card-title">
          <h3>Présentez-vous</h3>
          <span className="muted">{words} mots · ≈ {Math.max(1, Math.round(words / 130))} min à l'oral</span>
          <CopyButton text={prep.pitch} />
        </div>
        <p className="prose"><WithBlanks text={prep.pitch} /></p>
      </div>

      {prep.messages_cles.length > 0 && (
        <div className="card">
          <h3>Messages clés à faire passer</h3>
          <ul className="good">{prep.messages_cles.map((m, i) => <li key={i}>{m}</li>)}</ul>
        </div>
      )}

      {groups.map(([cat, questions]) => (
        <section key={cat}>
          <h3>{CATEGORIES[cat]} <span className="muted">({questions.length})</span></h3>
          {questions.map((q, i) => (
            <details key={i} className="card question">
              <summary>{q.question}</summary>
              <div className="card-body">
                {q.pourquoi && <p className="muted">Ce qui est vérifié : {q.pourquoi}</p>}
                <p className="prose"><WithBlanks text={q.piste_reponse} /></p>
                {q.appuis.length > 0 && (
                  <div className="chips">
                    <strong>Appuis :</strong> {q.appuis.map((a) => <span key={a} className="chip light">{a}</span>)}
                  </div>
                )}
              </div>
            </details>
          ))}
        </section>
      ))}

      <div className="two-cols">
        <div className="card">
          <h3>Points de vigilance</h3>
          <ul className="bad">{prep.points_vigilance.map((p, i) => <li key={i}>{p}</li>)}</ul>
        </div>
        <div className="card">
          <div className="card-title">
            <h3>Questions à poser</h3>
            <CopyButton text={prep.questions_a_poser.map((q) => `- ${q}`).join("\n")} label="Copier" />
          </div>
          <ul>{prep.questions_a_poser.map((q, i) => <li key={i}>{q}</li>)}</ul>
        </div>
      </div>
    </>
  );
}

type DebriefFields = Pick<Interview, "scheduled_at" | "context" | "interviewers" | "questions_asked" | "notes" | "feeling" | "next_steps">;

const debriefOf = (i: Interview): DebriefFields => ({
  scheduled_at: i.scheduled_at,
  context: i.context,
  interviewers: i.interviewers,
  questions_asked: i.questions_asked,
  notes: i.notes,
  feeling: i.feeling,
  next_steps: i.next_steps,
});

function Debrief({ interview, onSaved }: { interview: Interview; onSaved: () => Promise<unknown> }) {
  const [saved, setSaved] = useState(() => debriefOf(interview));
  const [draft, setDraft] = useState(saved);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const dirty = JSON.stringify(draft) !== JSON.stringify(saved);
  const set = <K extends keyof DebriefFields>(key: K) => (value: DebriefFields[K]) => setDraft({ ...draft, [key]: value });

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const updated = await api.updateInterview(interview.id, draft);
      setSaved(debriefOf(updated));
      setDraft(debriefOf(updated));
      await onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <aside className="card interview-debrief">
      <h3>Infos et débrief</h3>
      <label className="field">
        <span className="field-label">Date et heure</span>
        <input type="datetime-local" value={toLocalInput(draft.scheduled_at)}
               onChange={(e) => set("scheduled_at")(fromLocalInput(e.target.value))} />
      </label>
      <Field label="Contexte connu avant l'entretien" value={draft.context} onChange={set("context")} multiline rows={2} />
      <Field label="Interlocuteurs" value={draft.interviewers} onChange={set("interviewers")}
             placeholder="ex. Claire (RH), Marc (lead dev)" />
      <label className="field">
        <span className="field-label">Ressenti</span>
        <select value={draft.feeling} onChange={(e) => set("feeling")(e.target.value as InterviewFeeling)}>
          {Object.entries(FEELINGS).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
        </select>
      </label>
      <Field label="Questions réellement posées" value={draft.questions_asked} onChange={set("questions_asked")}
             multiline rows={4} hint="Elles serviront à préparer le tour suivant." />
      <Field label="Notes" value={draft.notes} onChange={set("notes")} multiline rows={4} />
      <Field label="Suite annoncée" value={draft.next_steps} onChange={set("next_steps")}
             placeholder="ex. réponse sous 10 jours, test technique à faire" />
      {error && <div className="alert error">{error}</div>}
      <div className="toolbar">
        <button className="primary" disabled={!dirty || saving} onClick={save}>{saving ? "Enregistrement…" : "Enregistrer"}</button>
        {dirty && <span className="muted">Non enregistré</span>}
      </div>
    </aside>
  );
}
