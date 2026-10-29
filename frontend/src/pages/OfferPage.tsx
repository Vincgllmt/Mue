import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import { CvForm, LetterForm } from "../components/DocForms";
import { Field } from "../components/forms";
import { JobStatus, useJob } from "../components/job";
import { CopyButton, Score, StatusSelect, VerdictBadge, Warnings, formatDateTime } from "../components/ui";
import type { CvContent, GeneratedDoc, LetterContent, Offer, OfferAnalysis } from "../types";

export default function OfferPage() {
  const id = Number(useParams().id);
  const navigate = useNavigate();
  const [offer, setOffer] = useState<Offer | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"cv" | "letter">("cv");

  const [autoCvJob, setAutoCvJob] = useState<number | null>(null);

  const reload = () => api.offer(id).then((o) => { setOffer(o); return o; }).catch((e) => { setError(e.message); return null; });
  // Analyse terminée : on enchaîne sur le CV, sauf verdict « ne pas postuler ».
  const analysis = useJob(async () => {
    const o = await reload();
    if (o && o.verdict !== "ne_pas_postuler" && !o.application?.docs.some((d) => d.kind === "cv")) {
      const { job_id } = await api.generateCv(o.id);
      setAutoCvJob(job_id);
    }
  });

  useEffect(() => {
    reload().then((o) => {
      const job = o?.analysis_job;
      if (job && (job.status === "pending" || job.status === "running" || job.status === "error")) analysis.follow(job.id);
    });
  }, [id]);

  if (error) return <div className="alert error">{error}</div>;
  if (!offer) return <p className="muted">Chargement…</p>;

  const a = offer.analysis;
  const remove = async () => {
    if (!window.confirm("Supprimer cette offre et ses documents ?")) return;
    await api.deleteOffer(offer.id);
    navigate("/");
  };

  return (
    <section>
      <div className="page-head">
        <div>
          <Link to="/" className="muted">← Candidatures</Link>
          <h1>{a ? `${a.poste} — ${a.entreprise}` : "Analyse de l'offre"}</h1>
          {offer.url && <a href={offer.url} target="_blank" rel="noreferrer" className="muted">{offer.url}</a>}
        </div>
        <div className="head-actions">
          {offer.application && (
            <StatusSelect
              value={offer.application.status}
              onChange={async (s) => {
                const app = await api.setStatus(offer.application!.id, s);
                setOffer({ ...offer, application: app });
              }}
            />
          )}
          {offer.application && (
            <span className="muted status-date">depuis le {formatDateTime(offer.application.status_changed_at)}</span>
          )}
          <button className="danger small" onClick={remove}>Supprimer</button>
        </div>
      </div>

      <JobStatus job={analysis.job} error={analysis.error} onRetry={analysis.retry} />
      {a && <AnalysisPanel analysis={a} rawText={offer.raw_text ?? ""} />}

      {a && (
        <>
          <div className="tabs">
            <button className={tab === "cv" ? "active" : ""} onClick={() => setTab("cv")}>CV adapté</button>
            <button className={tab === "letter" ? "active" : ""} onClick={() => setTab("letter")}>Lettre de motivation</button>
          </div>
          {tab === "cv" ? <CvTab offer={offer} reload={reload} autoJob={autoCvJob} /> : <LetterTab offer={offer} reload={reload} />}
        </>
      )}
    </section>
  );
}

function AnalysisPanel({ analysis: a, rawText }: { analysis: OfferAnalysis; rawText: string }) {
  return (
    <div className="analysis card">
      <div className="analysis-head">
        <Score value={a.score_matching} />
        <VerdictBadge verdict={a.verdict} />
        <span className="muted">{[a.lieu, a.contrat, a.teletravail && `Télétravail : ${a.teletravail}`, a.seniorite].filter(Boolean).join(" · ")}</span>
      </div>
      <p>{a.justification}</p>
      <div className="two-cols">
        <div>
          <h4>Points forts</h4>
          <ul className="good">{a.points_forts.map((p, i) => <li key={i}>{p}</li>)}</ul>
        </div>
        <div>
          <h4>Écarts</h4>
          <ul className="bad">{a.ecarts.map((p, i) => <li key={i}>{p}</li>)}</ul>
        </div>
      </div>
      <div className="chips">
        <strong>Stack requise :</strong> {a.stack_requise.map((s) => <span key={s} className="chip">{s}</span>)}
      </div>
      {a.stack_bonus.length > 0 && (
        <div className="chips">
          <strong>Bonus :</strong> {a.stack_bonus.map((s) => <span key={s} className="chip light">{s}</span>)}
        </div>
      )}
      <div className="chips">
        <strong>Mots-clés ATS :</strong> {a.mots_cles_ats.map((s) => <span key={s} className="chip light">{s}</span>)}
      </div>
      <details>
        <summary className="muted">Texte de l'offre</summary>
        <pre className="raw">{rawText}</pre>
      </details>
    </div>
  );
}

function NoGoNotice({ offer }: { offer: Offer }) {
  if (offer.verdict !== "ne_pas_postuler") return null;
  return (
    <div className="alert warning">
      Verdict « ne pas postuler » : la génération n'est pas lancée automatiquement. Tu peux quand même générer les documents.
    </div>
  );
}

/** Sélection d'une version d'un document parmi celles générées. */
function useDocSelection(offer: Offer, kind: GeneratedDoc["kind"]) {
  const docs = (offer.application?.docs ?? []).filter((d) => d.kind === kind);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const doc = docs.find((d) => d.id === selectedId) ?? docs[0] ?? null;
  return { docs, doc, select: setSelectedId };
}

function VersionPicker({ docs, doc, select }: { docs: GeneratedDoc[]; doc: GeneratedDoc | null; select: (id: number) => void }) {
  if (docs.length < 2 || !doc) return null;
  return (
    <select value={doc.id} onChange={(e) => select(Number(e.target.value))}>
      {docs.map((d, i) => <option key={d.id} value={d.id}>Version {docs.length - i} — {formatDateTime(d.created_at)}</option>)}
    </select>
  );
}

function CvTab({ offer, reload, autoJob }: { offer: Offer; reload: () => Promise<Offer | null>; autoJob: number | null }) {
  const { docs, doc, select } = useDocSelection(offer, "cv");
  const gen = useJob(async (job) => { await reload(); select(job.result?.doc_id); });
  const noGo = offer.verdict === "ne_pas_postuler";

  useEffect(() => {
    if (autoJob) gen.follow(autoJob);
  }, [autoJob]);

  return (
    <div>
      <NoGoNotice offer={offer} />
      <div className="toolbar">
        <button className="primary" disabled={gen.running} onClick={() => gen.start(() => api.generateCv(offer.id, noGo))}>
          {doc ? "Régénérer le CV" : noGo ? "Générer quand même" : "Générer le CV"}
        </button>
        <VersionPicker docs={docs} doc={doc} select={select} />
      </div>
      <JobStatus job={gen.job} error={gen.error} onRetry={gen.retry} />
      {doc && <DocEditor key={doc.id} doc={doc} onSaved={reload}
        form={(v, set) => <CvForm value={v as CvContent} onChange={set} />} />}
    </div>
  );
}

function LetterTab({ offer, reload }: { offer: Offer; reload: () => Promise<Offer | null> }) {
  const { docs, doc, select } = useDocSelection(offer, "letter");
  const shortDocs = (offer.application?.docs ?? []).filter((d) => d.kind === "letter_short");
  const [ton, setTon] = useState("neutre");
  const [longueur, setLongueur] = useState("standard");
  const [focus, setFocus] = useState("");
  const [short, setShort] = useState(true);
  const gen = useJob(async (job) => { await reload(); select(job.result?.doc_id); });
  const noGo = offer.verdict === "ne_pas_postuler";

  return (
    <div>
      <NoGoNotice offer={offer} />
      <div className="card options">
        <label className="field inline">
          <span className="field-label">Ton</span>
          <select value={ton} onChange={(e) => setTon(e.target.value)}>
            <option value="formel">Formel</option>
            <option value="neutre">Neutre</option>
            <option value="direct">Direct</option>
          </select>
        </label>
        <label className="field inline">
          <span className="field-label">Longueur</span>
          <select value={longueur} onChange={(e) => setLongueur(e.target.value)}>
            <option value="courte">Courte (~150 mots)</option>
            <option value="standard">Standard (~250 mots)</option>
          </select>
        </label>
        <label className="checkbox">
          <input type="checkbox" checked={short} onChange={(e) => setShort(e.target.checked)} /> Variante courte (~80 mots)
        </label>
        <Field label="Éléments à mettre en avant (optionnel)" value={focus} onChange={setFocus}
               placeholder="ex. mon expérience en TMA, le projet de migration…" />
        <div className="toolbar">
          <button className="primary" disabled={gen.running}
                  onClick={() => gen.start(() => api.generateLetter(offer.id, { ton, longueur, focus, short, force: noGo }))}>
            {doc ? "Régénérer la lettre" : noGo ? "Générer quand même" : "Générer la lettre"}
          </button>
          <VersionPicker docs={docs} doc={doc} select={select} />
        </div>
      </div>
      <JobStatus job={gen.job} error={gen.error} onRetry={gen.retry} />
      {doc && <DocEditor key={doc.id} doc={doc} onSaved={reload}
        form={(v, set) => <LetterForm value={v as LetterContent} onChange={set} />} />}
      {shortDocs[0] && <ShortLetter key={shortDocs[0].id} doc={shortDocs[0]} onSaved={reload} />}
    </div>
  );
}

function DocEditor({
  doc, form, onSaved,
}: {
  doc: GeneratedDoc;
  form: (value: unknown, set: (v: any) => void) => React.ReactNode;
  onSaved: () => Promise<unknown>;
}) {
  const [draft, setDraft] = useState(doc.content);
  const [current, setCurrent] = useState(doc);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const dirty = JSON.stringify(draft) !== JSON.stringify(current.content);

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      const saved = await api.saveDoc(doc.id, draft);
      setCurrent(saved);
      setDraft(saved.content);
      await onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="editor">
      <div className="editor-left">
        <Warnings warnings={current.warnings} />
        <div className="toolbar sticky">
          <button className="primary" disabled={!dirty || saving} onClick={save}>
            {saving ? "Rendu…" : "Enregistrer et régénérer le PDF"}
          </button>
          {dirty && <span className="muted">Modifications non enregistrées</span>}
          {current.pdf_url && <a className="button" href={`/api/docs/${doc.id}/pdf?download=1`}>Télécharger le PDF</a>}
          {current.text && <CopyButton text={current.text} />}
        </div>
        {error && <div className="alert error">{error}</div>}
        {form(draft, setDraft)}
      </div>
      <div className="editor-right">
        {current.pdf_url ? <iframe title="Aperçu PDF" src={current.pdf_url} /> : <p className="muted">Pas de PDF.</p>}
      </div>
    </div>
  );
}

function ShortLetter({ doc, onSaved }: { doc: GeneratedDoc; onSaved: () => Promise<unknown> }) {
  const [text, setText] = useState<string>(doc.content.texte);
  const [saved, setSaved] = useState<string>(doc.content.texte);
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  return (
    <div className="card short-letter">
      <h3>Variante courte (LinkedIn, e-mail) — {words} mots</h3>
      <textarea rows={6} value={text} onChange={(e) => setText(e.target.value)} />
      <div className="toolbar">
        <button disabled={text === saved} onClick={async () => {
          await api.saveDoc(doc.id, { texte: text });
          setSaved(text);
          await onSaved();
        }}>Enregistrer</button>
        <CopyButton text={text} />
      </div>
    </div>
  );
}
