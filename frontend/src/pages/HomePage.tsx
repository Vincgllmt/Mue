import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { STATUSES, Score, StatusSelect, VERDICTS, VerdictBadge, formatDate } from "../components/ui";
import type { ApplicationStatus, Offer } from "../types";

const DOC_LABELS = { cv: "CV", letter: "Lettre", letter_short: "Message court" } as const;

type SortKey = "date" | "poste" | "score" | "verdict" | "status" | "status_changed";
type Sort = { key: SortKey; dir: 1 | -1 };

const SORT_STORAGE = "mue.home.sort";
const STATUS_ORDER = Object.keys(STATUSES);
const VERDICT_ORDER = Object.keys(VERDICTS);

/** Valeur de tri d'une offre ; null = toujours en fin de liste. */
function sortValue(o: Offer, key: SortKey): string | number | null {
  switch (key) {
    case "date": return o.created_at;
    case "poste": return o.analysis?.poste?.toLocaleLowerCase("fr") || null;
    case "score": return o.score;
    case "verdict": return o.verdict ? VERDICT_ORDER.indexOf(o.verdict) : null;
    case "status": return o.application ? STATUS_ORDER.indexOf(o.application.status) : null;
    case "status_changed": return o.application?.status_changed_at ?? null;
  }
}

function sortOffers(offers: Offer[], { key, dir }: Sort) {
  return [...offers].sort((a, b) => {
    const va = sortValue(a, key), vb = sortValue(b, key);
    if (va === vb) return b.created_at.localeCompare(a.created_at);
    if (va === null) return 1;
    if (vb === null) return -1;
    return (typeof va === "string" ? va.localeCompare(vb as string, "fr") : va - (vb as number)) * dir;
  });
}

function loadSort(): Sort {
  try {
    const s = JSON.parse(localStorage.getItem(SORT_STORAGE) ?? "");
    if (s && s.key && (s.dir === 1 || s.dir === -1)) return s;
  } catch {}
  return { key: "date", dir: -1 };
}

export default function HomePage() {
  const [offers, setOffers] = useState<Offer[] | null>(null);
  const [error, setError] = useState("");
  const [sort, setSort] = useState<Sort>(loadSort);
  const navigate = useNavigate();

  const toggleSort = (key: SortKey) => {
    // Premier clic : décroissant pour les dates et le score, croissant pour le reste.
    const dir = sort.key === key ? (-sort.dir as 1 | -1) : ["date", "score", "status_changed"].includes(key) ? -1 : 1;
    const next = { key, dir } as Sort;
    setSort(next);
    try {
      localStorage.setItem(SORT_STORAGE, JSON.stringify(next));
    } catch {}
  };
  const th = (key: SortKey, label: string) => (
    <th className={`sortable ${sort.key === key ? "active" : ""}`} onClick={() => toggleSort(key)}>
      {label} {sort.key === key ? (sort.dir === 1 ? "▲" : "▼") : ""}
    </th>
  );

  const load = () => api.offers().then(setOffers).catch((e) => setError(e.message));
  useEffect(() => {
    load();
  }, []);

  // Rafraîchit tant qu'une analyse est en cours.
  const analysing = offers?.some((o) => o.analysis_job && ["pending", "running"].includes(o.analysis_job.status));
  useEffect(() => {
    if (!analysing) return;
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [analysing]);

  const setStatus = async (offer: Offer, status: ApplicationStatus) => {
    if (!offer.application) return;
    const app = await api.setStatus(offer.application.id, status);
    setOffers((list) => list?.map((o) => (o.id === offer.id ? { ...o, application: app } : o)) ?? null);
  };

  return (
    <section>
      <div className="page-head">
        <h1>Candidatures</h1>
        <button className="primary" onClick={() => navigate("/offers/new")}>+ Nouvelle offre</button>
      </div>
      {error && <div className="alert error">{error}</div>}
      {offers === null && !error && <p className="muted">Chargement…</p>}
      {offers?.length === 0 && (
        <div className="empty">
          <p>Aucune offre analysée pour l'instant.</p>
          <p className="muted">Commence par remplir ton <Link to="/profile">profil maître</Link>, puis colle une offre.</p>
        </div>
      )}
      {!!offers?.length && (
        <table className="table">
          <thead>
            <tr>
              {th("date", "Date")}
              {th("poste", "Poste")}
              {th("score", "Score")}
              {th("verdict", "Verdict")}
              <th>Documents</th>
              {th("status", "Statut")}
              {th("status_changed", "Changement")}
            </tr>
          </thead>
          <tbody>
            {sortOffers(offers, sort).map((o) => (
              <tr key={o.id}>
                <td className="nowrap">{formatDate(o.created_at)}</td>
                <td>
                  <Link to={`/offers/${o.id}`}>
                    <strong>{o.analysis?.poste || "Offre en cours d'analyse"}</strong>
                  </Link>
                  <div className="muted">{[o.analysis?.entreprise, o.analysis?.lieu].filter(Boolean).join(" · ")}</div>
                  {o.analysis_job?.status === "error" && <div className="error-text">Analyse en échec</div>}
                </td>
                <td><Score value={o.score} /></td>
                <td><VerdictBadge verdict={o.verdict} /></td>
                <td className="docs">
                  {latestDocs(o).map((d) =>
                    d.pdf_url ? (
                      <a key={d.id} href={`/api/docs/${d.id}/pdf?download=1`}>{DOC_LABELS[d.kind]} ↓</a>
                    ) : (
                      <Link key={d.id} to={`/offers/${o.id}`}>{DOC_LABELS[d.kind]}</Link>
                    ),
                  )}
                </td>
                <td>
                  {o.application && <StatusSelect value={o.application.status} onChange={(s) => setStatus(o, s)} />}
                </td>
                <td className="nowrap muted">{formatDate(o.application?.status_changed_at ?? null)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

/** Le document le plus récent de chaque type. */
function latestDocs(o: Offer) {
  const seen = new Set<string>();
  return (o.application?.docs ?? []).filter((d) => !seen.has(d.kind) && seen.add(d.kind));
}
