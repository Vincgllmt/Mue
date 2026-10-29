import { useState } from "react";
import type { ApplicationStatus, GuardWarning, Verdict } from "../types";

export const VERDICTS: Record<Verdict, { label: string; tone: string }> = {
  postuler: { label: "Postuler", tone: "green" },
  postuler_avec_reserve: { label: "Postuler avec réserve", tone: "orange" },
  ne_pas_postuler: { label: "Ne pas postuler", tone: "red" },
};

export const STATUSES: Record<ApplicationStatus, string> = {
  brouillon: "Brouillon",
  non_postule: "Non postulé",
  envoyee: "Envoyée",
  entretien: "Entretien",
  refus: "Refus",
};

export function VerdictBadge({ verdict }: { verdict: Verdict | "" }) {
  if (!verdict) return <span className="badge gray">En analyse</span>;
  const v = VERDICTS[verdict];
  return <span className={`badge ${v.tone}`}>{v.label}</span>;
}

export function Score({ value }: { value: number | null }) {
  if (value === null) return <span className="muted">—</span>;
  const tone = value >= 70 ? "green" : value >= 45 ? "orange" : "red";
  return <span className={`score ${tone}`}>{value}</span>;
}

export function StatusSelect({ value, onChange }: { value: ApplicationStatus; onChange: (v: ApplicationStatus) => void }) {
  return (
    <select value={value} onChange={(e) => onChange(e.target.value as ApplicationStatus)} className={`status ${value}`}>
      {Object.entries(STATUSES).map(([k, label]) => (
        <option key={k} value={k}>{label}</option>
      ))}
    </select>
  );
}

export function Warnings({ warnings }: { warnings: GuardWarning[] }) {
  if (!warnings.length) {
    return <div className="alert success">Garde-fou : aucune donnée absente du profil maître détectée.</div>;
  }
  const errors = warnings.filter((w) => w.niveau === "erreur");
  return (
    <div className={`alert ${errors.length ? "error" : "warning"}`}>
      <strong>Garde-fou anti-invention</strong> : {errors.length} erreur(s), {warnings.length - errors.length} avertissement(s)
      <ul>
        {warnings.map((w, i) => (
          <li key={i}>
            <code>{w.champ}</code> {w.message}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function CopyButton({ text, label = "Copier le texte" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
    >
      {copied ? "Copié ✓" : label}
    </button>
  );
}

export function formatDate(iso: string | null) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" });
}

export function formatDateTime(iso: string | null) {
  if (!iso) return "";
  return new Date(iso).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });
}
