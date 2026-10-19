import { useCallback, useEffect, useRef, useState } from "react";
import { api, waitForJob } from "../api";
import type { Job } from "../types";

const LABELS: Record<string, string> = {
  extract_profile: "Extraction du CV",
  analyze_offer: "Analyse de l'offre",
  generate_cv: "Génération du CV",
  generate_letter: "Génération de la lettre",
  audit: "Audit du CV",
};

/** Lance et suit un job asynchrone ; `onDone` reçoit le job terminé avec succès. */
export function useJob(onDone: (job: Job) => void) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");
  const abort = useRef<AbortController | null>(null);
  const done = useRef(onDone);
  done.current = onDone;

  useEffect(() => () => abort.current?.abort(), []);

  const follow = useCallback(async (jobId: number) => {
    abort.current?.abort();
    const ctrl = new AbortController();
    abort.current = ctrl;
    setError("");
    try {
      const final = await waitForJob(jobId, (j) => !ctrl.signal.aborted && setJob(j), ctrl.signal);
      if (!ctrl.signal.aborted && final.status === "done") done.current(final);
    } catch (e) {
      if ((e as Error).name !== "AbortError") setError((e as Error).message);
    }
  }, []);

  const start = useCallback(
    async (launch: () => Promise<{ job_id: number }>) => {
      setError("");
      setJob(null);
      try {
        const { job_id } = await launch();
        await follow(job_id);
      } catch (e) {
        setError((e as Error).message);
      }
    },
    [follow],
  );

  const retry = useCallback(async () => {
    if (!job) return;
    try {
      await api.retryJob(job.id);
      await follow(job.id);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [job, follow]);

  const running = !!job && (job.status === "pending" || job.status === "running");
  return { job, running, error, start, follow, retry, reset: () => { setJob(null); setError(""); } };
}

export function JobStatus({ job, error, onRetry }: { job: Job | null; error?: string; onRetry?: () => void }) {
  const [elapsed, setElapsed] = useState(0);
  const running = !!job && (job.status === "pending" || job.status === "running");

  useEffect(() => {
    if (!running) return;
    const t0 = Date.now();
    setElapsed(0);
    const t = setInterval(() => setElapsed(Math.round((Date.now() - t0) / 1000)), 1000);
    return () => clearInterval(t);
  }, [running, job?.id]);

  if (error) return <div className="alert error">{error}</div>;
  if (!job) return null;
  const label = LABELS[job.kind] ?? job.kind;
  if (running) {
    return (
      <div className="alert info">
        <span className="spinner" /> {label} {job.status === "pending" ? "en file d'attente" : "en cours"}… {elapsed} s
      </div>
    );
  }
  if (job.status === "error") {
    return (
      <div className="alert error">
        <strong>{label} : échec.</strong> {job.error}
        {onRetry && <button className="small" onClick={onRetry}>Relancer</button>}
      </div>
    );
  }
  return null;
}
