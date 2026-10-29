import type {
  Application, Audit, GeneratedDoc, Job, Offer, ProfileData, ProfileResponse, ProfileVersion, Suggestion,
} from "./types";

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

async function request<T>(method: string, url: string, body?: unknown): Promise<T> {
  const init: RequestInit = { method, headers: {} };
  if (body instanceof FormData) {
    init.body = body;
  } else if (body !== undefined) {
    init.body = JSON.stringify(body);
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
  }
  let res: Response;
  try {
    res = await fetch(`/api${url}`, init);
  } catch {
    throw new ApiError("Serveur injoignable : le back-end Django est-il lancé ?", 0);
  }
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail ?? Object.values(data).flat().join(" ") ?? res.statusText;
    throw new ApiError(String(detail || `Erreur ${res.status}`), res.status);
  }
  return data as T;
}

type JobStart = { job_id: number };

export const api = {
  getProfile: () => request<ProfileResponse>("GET", "/profile"),
  saveProfile: (data: ProfileData, note?: string) => request<ProfileResponse>("PUT", "/profile", { data, note }),
  importCv: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<JobStart>("POST", "/profile/import", form);
  },
  versions: () => request<ProfileVersion[]>("GET", "/profile/versions"),
  version: (v: number) => request<ProfileResponse>("GET", `/profile/versions/${v}`),
  restoreVersion: (v: number) => request<ProfileResponse>("POST", `/profile/versions/${v}/restore`),

  offers: () => request<Offer[]>("GET", "/offers"),
  offer: (id: number) => request<Offer>("GET", `/offers/${id}`),
  createOffer: (raw_text: string, url: string, job_title: string) =>
    request<{ offer: Offer; job_id: number }>("POST", "/offers", { raw_text, url, job_title }),
  deleteOffer: (id: number) => request<void>("DELETE", `/offers/${id}`),
  generateCv: (id: number, force = false) => request<JobStart>("POST", `/offers/${id}/generate-cv`, { force }),
  generateLetter: (id: number, params: { ton: string; longueur: string; focus: string; short: boolean; force: boolean }) =>
    request<JobStart>("POST", `/offers/${id}/generate-letter`, params),

  doc: (id: number) => request<GeneratedDoc>("GET", `/docs/${id}`),
  saveDoc: (id: number, content: unknown) => request<GeneratedDoc>("PUT", `/docs/${id}`, { content }),
  deleteDoc: (id: number) => request<void>("DELETE", `/docs/${id}`),

  audits: () => request<Audit[]>("GET", "/audits"),
  audit: (id: number) => request<Audit>("GET", `/audits/${id}`),
  startAudit: (target_role: string, file?: File | null) => {
    const form = new FormData();
    form.append("target_role", target_role);
    if (file) form.append("file", file);
    return request<{ audit: Audit; job_id: number }>("POST", "/audits", form);
  },
  updateSuggestion: (id: number, state: Suggestion["state"], after?: string) =>
    request<Suggestion>("PATCH", `/suggestions/${id}`, { state, after }),
  respondSuggestion: (id: number, response: string) => request<Suggestion>("PATCH", `/suggestions/${id}`, { response }),
  reviseAudit: (id: number) => request<JobStart>("POST", `/audits/${id}/revise`),
  applyRevision: (id: number) => request<Audit>("POST", `/audits/${id}/revision/apply`),

  job: (id: number) => request<Job>("GET", `/jobs/${id}`),
  retryJob: (id: number) => request<Job>("POST", `/jobs/${id}/retry`),
  setStatus: (id: number, status: string) => request<Application>("PATCH", `/applications/${id}`, { status }),
};

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Interroge un job toutes les 2 s jusqu'à `done` ou `error`. */
export async function waitForJob(id: number, onUpdate?: (job: Job) => void, signal?: AbortSignal): Promise<Job> {
  for (;;) {
    const job = await api.job(id);
    onUpdate?.(job);
    if (job.status === "done" || job.status === "error") return job;
    if (signal?.aborted) throw new DOMException("Annulé", "AbortError");
    await sleep(2000);
  }
}
