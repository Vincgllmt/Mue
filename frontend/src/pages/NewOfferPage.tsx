import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { Field } from "../components/forms";

export default function NewOfferPage() {
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { offer } = await api.createOffer(text, url, jobTitle);
      navigate(`/offers/${offer.id}`);
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };

  return (
    <section className="narrow">
      <h1>Nouvelle offre</h1>
      <p className="muted">Colle le texte complet de l'offre. Mue l'analyse et donne un avis go / no-go avant toute génération.</p>
      <form onSubmit={submit}>
        <Field label="Nom du poste (optionnel)" value={jobTitle} onChange={setJobTitle}
               placeholder="ex. Développeur back-end Python"
               hint="Utilisé tel quel comme titre du CV. Laisse vide pour que Mue propose un titre adapté à l'offre." />
        <Field label="Texte de l'offre" value={text} onChange={setText} multiline rows={18}
               placeholder="Intitulé, entreprise, missions, profil recherché, stack…" />
        <Field label="URL (optionnelle, pour référence)" value={url} onChange={setUrl} placeholder="https://…"
               hint="Elle n'est pas consultée automatiquement." />
        {error && <div className="alert error">{error}</div>}
        <button className="primary" disabled={busy || text.trim().length < 100}>
          {busy ? "Envoi…" : "Analyser l'offre"}
        </button>
        {text.trim().length > 0 && text.trim().length < 100 && <span className="muted"> Texte trop court.</span>}
      </form>
    </section>
  );
}
