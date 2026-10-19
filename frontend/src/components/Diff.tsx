type Part = { type: "same" | "del" | "add"; text: string };

/** Diff mot à mot (plus longue sous-séquence commune). */
export function diffWords(a: string, b: string): Part[] {
  const x = a.split(/(\s+)/);
  const y = b.split(/(\s+)/);
  const n = x.length;
  const m = y.length;
  const lcs = Array.from({ length: n + 1 }, () => new Array<number>(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      lcs[i][j] = x[i] === y[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    }
  }
  const parts: Part[] = [];
  const push = (type: Part["type"], text: string) => {
    const last = parts[parts.length - 1];
    if (last && last.type === type) last.text += text;
    else parts.push({ type, text });
  };
  let i = 0;
  let j = 0;
  while (i < n && j < m) {
    if (x[i] === y[j]) { push("same", x[i]); i++; j++; }
    else if (lcs[i + 1][j] >= lcs[i][j + 1]) push("del", x[i++]);
    else push("add", y[j++]);
  }
  while (i < n) push("del", x[i++]);
  while (j < m) push("add", y[j++]);
  return parts;
}

export function Diff({ before, after }: { before: string; after: string }) {
  if (!after) return <p className="diff">{before}</p>;
  return (
    <p className="diff">
      {diffWords(before, after).map((p, i) =>
        p.type === "same" ? <span key={i}>{p.text}</span> : p.type === "del" ? <del key={i}>{p.text}</del> : <ins key={i}>{p.text}</ins>,
      )}
    </p>
  );
}
