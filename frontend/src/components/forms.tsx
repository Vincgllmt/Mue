import type { ReactNode } from "react";

interface FieldProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  multiline?: boolean;
  rows?: number;
  hint?: string;
}

export function Field({ label, value, onChange, placeholder, multiline, rows = 3, hint }: FieldProps) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {multiline ? (
        <textarea value={value ?? ""} rows={rows} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
      ) : (
        <input value={value ?? ""} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
      )}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

/** Liste de chaînes : une ligne par élément (puces, stack, centres d'intérêt). */
export function StringList({
  label, items, onChange, multiline, placeholder,
}: {
  label: string;
  items: string[];
  onChange: (items: string[]) => void;
  multiline?: boolean;
  placeholder?: string;
}) {
  const set = (i: number, v: string) => onChange(items.map((x, j) => (j === i ? v : x)));
  return (
    <div className="field">
      <span className="field-label">{label}</span>
      {items.map((item, i) => (
        <div className="list-row" key={i}>
          {multiline ? (
            <textarea rows={2} value={item} placeholder={placeholder} onChange={(e) => set(i, e.target.value)} />
          ) : (
            <input value={item} placeholder={placeholder} onChange={(e) => set(i, e.target.value)} />
          )}
          <button type="button" className="icon" title="Monter" disabled={i === 0} onClick={() => onChange(move(items, i, -1))}>↑</button>
          <button type="button" className="icon" title="Supprimer" onClick={() => onChange(items.filter((_, j) => j !== i))}>✕</button>
        </div>
      ))}
      <button type="button" className="link" onClick={() => onChange([...items, ""])}>+ Ajouter</button>
    </div>
  );
}

/** Saisie compacte « a, b, c » pour les stacks. */
export function CommaList({ label, items, onChange }: { label: string; items: string[]; onChange: (v: string[]) => void }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      <input
        defaultValue={items.join(", ")}
        key={items.join("|")}
        onBlur={(e) => onChange(e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
        placeholder="Python, Django, PostgreSQL"
      />
    </label>
  );
}

export function move<T>(items: T[], i: number, delta: number): T[] {
  const j = i + delta;
  if (j < 0 || j >= items.length) return items;
  const copy = [...items];
  [copy[i], copy[j]] = [copy[j], copy[i]];
  return copy;
}

/** Liste d'objets éditables (expériences, formations…). */
export function ObjectList<T>({
  items, onChange, empty, render, title, addLabel = "+ Ajouter",
}: {
  items: T[];
  onChange: (items: T[]) => void;
  empty: () => T;
  render: (item: T, update: (patch: Partial<T>) => void, index: number) => ReactNode;
  title: (item: T, index: number) => string;
  addLabel?: string;
}) {
  return (
    <div className="object-list">
      {items.map((item, i) => (
        <details className="card" key={i} open={items.length <= 2}>
          <summary>
            <span>{title(item, i) || "(sans titre)"}</span>
            <span className="row-actions" onClick={(e) => e.preventDefault()}>
              <button type="button" className="icon" title="Monter" disabled={i === 0} onClick={() => onChange(move(items, i, -1))}>↑</button>
              <button type="button" className="icon" title="Descendre" disabled={i === items.length - 1} onClick={() => onChange(move(items, i, 1))}>↓</button>
              <button type="button" className="icon" title="Supprimer" onClick={() => onChange(items.filter((_, j) => j !== i))}>✕</button>
            </span>
          </summary>
          <div className="card-body">
            {render(item, (patch) => onChange(items.map((x, j) => (j === i ? { ...x, ...patch } : x))), i)}
          </div>
        </details>
      ))}
      <button type="button" className="link" onClick={() => onChange([...items, empty()])}>{addLabel}</button>
    </div>
  );
}

export function Row({ children }: { children: ReactNode }) {
  return <div className="row">{children}</div>;
}
