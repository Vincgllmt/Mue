import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { Score, StatusSelect, VerdictBadge, formatDate } from "../components/ui";
import type { ApplicationStatus, Offer } from "../types";

const DOC_LABELS = { cv: "CV", letter: "Lettre", letter_short: "Message court" } as const;

export default function HomePage() {
  const [offers, setOffers] = useState<Offer[] | null>(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

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
              <th>Date</th>
              <th>Poste</th>
              <th>Score</th>
              <th>Verdict</th>
              <th>Documents</th>
              <th>Statut</th>
            </tr>
          </thead>
          <tbody>
            {offers.map((o) => (
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
