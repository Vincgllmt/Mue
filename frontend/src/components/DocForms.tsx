import { CommaList, Field, ObjectList, Row, StringList } from "./forms";
import type { CvContent, LetterContent } from "../types";

export function CvForm({ value, onChange }: { value: CvContent; onChange: (v: CvContent) => void }) {
  const set = (patch: Partial<CvContent>) => onChange({ ...value, ...patch });
  return (
    <div className="doc-form">
      <Field label="Titre" value={value.titre} onChange={(titre) => set({ titre })} />
      <Field label="Accroche" value={value.accroche} onChange={(accroche) => set({ accroche })} multiline />

      <h3>Expériences</h3>
      <ObjectList
        items={value.experiences}
        onChange={(experiences) => set({ experiences })}
        title={(e) => `${e.poste} — ${e.entreprise}`}
        empty={() => ({ poste: "", entreprise: "", lieu: "", date_debut: "", date_fin: "", realisations: [], stack: [] })}
        render={(e, up) => (
          <>
            <Row>
              <Field label="Poste" value={e.poste} onChange={(poste) => up({ poste })} />
              <Field label="Entreprise" value={e.entreprise} onChange={(entreprise) => up({ entreprise })} />
            </Row>
            <Row>
              <Field label="Lieu" value={e.lieu} onChange={(lieu) => up({ lieu })} />
              <Field label="Début" value={e.date_debut} onChange={(date_debut) => up({ date_debut })} placeholder="AAAA-MM" />
              <Field label="Fin" value={e.date_fin} onChange={(date_fin) => up({ date_fin })} placeholder="vide = en cours" />
            </Row>
            <StringList label="Réalisations" items={e.realisations} onChange={(realisations) => up({ realisations })} multiline />
            <CommaList label="Stack" items={e.stack} onChange={(stack) => up({ stack })} />
          </>
        )}
      />

      <h3>Projets</h3>
      <ObjectList
        items={value.projets}
        onChange={(projets) => set({ projets })}
        title={(p) => p.nom}
        empty={() => ({ nom: "", description: "", stack: [] })}
        render={(p, up) => (
          <>
            <Field label="Nom" value={p.nom} onChange={(nom) => up({ nom })} />
            <Field label="Description" value={p.description} onChange={(description) => up({ description })} multiline rows={2} />
            <CommaList label="Stack" items={p.stack} onChange={(stack) => up({ stack })} />
          </>
        )}
      />

      <h3>Compétences</h3>
      <ObjectList
        items={value.competences}
        onChange={(competences) => set({ competences })}
        title={(c) => c.categorie}
        empty={() => ({ categorie: "", items: [] })}
        render={(c, up) => (
          <>
            <Field label="Catégorie" value={c.categorie} onChange={(categorie) => up({ categorie })} />
            <CommaList label="Éléments" items={c.items} onChange={(items) => up({ items })} />
          </>
        )}
      />

      <h3>Formation</h3>
      <ObjectList
        items={value.formations}
        onChange={(formations) => set({ formations })}
        title={(f) => `${f.diplome} — ${f.etablissement}`}
        empty={() => ({ diplome: "", etablissement: "", date_debut: "", date_fin: "", details: "" })}
        render={(f, up) => (
          <>
            <Row>
              <Field label="Diplôme" value={f.diplome} onChange={(diplome) => up({ diplome })} />
              <Field label="Établissement" value={f.etablissement} onChange={(etablissement) => up({ etablissement })} />
            </Row>
            <Row>
              <Field label="Début" value={f.date_debut} onChange={(date_debut) => up({ date_debut })} />
              <Field label="Fin" value={f.date_fin} onChange={(date_fin) => up({ date_fin })} />
            </Row>
            <Field label="Détails" value={f.details} onChange={(details) => up({ details })} />
          </>
        )}
      />

      <h3>Langues et centres d'intérêt</h3>
      <ObjectList
        items={value.langues}
        onChange={(langues) => set({ langues })}
        title={(l) => `${l.langue} ${l.niveau}`}
        empty={() => ({ langue: "", niveau: "" })}
        render={(l, up) => (
          <Row>
            <Field label="Langue" value={l.langue} onChange={(langue) => up({ langue })} />
            <Field label="Niveau" value={l.niveau} onChange={(niveau) => up({ niveau })} />
          </Row>
        )}
      />
      <CommaList label="Centres d'intérêt" items={value.centres_interet} onChange={(centres_interet) => set({ centres_interet })} />
    </div>
  );
}

export function LetterForm({ value, onChange }: { value: LetterContent; onChange: (v: LetterContent) => void }) {
  const set = (patch: Partial<LetterContent>) => onChange({ ...value, ...patch });
  return (
    <div className="doc-form">
      <Row>
        <Field label="Destinataire" value={value.destinataire} onChange={(destinataire) => set({ destinataire })} multiline rows={2} />
        <Field label="Lieu et date" value={value.lieu_date} onChange={(lieu_date) => set({ lieu_date })} />
      </Row>
      <Field label="Objet" value={value.objet} onChange={(objet) => set({ objet })} />
      <Field label="Salutation" value={value.salutation} onChange={(salutation) => set({ salutation })} />
      <StringList label="Paragraphes" items={value.paragraphes} onChange={(paragraphes) => set({ paragraphes })} multiline />
      <Field label="Formule de politesse" value={value.formule_politesse}
             onChange={(formule_politesse) => set({ formule_politesse })} multiline rows={2} />
    </div>
  );
}
