import type { Job, StatusFilter } from "./api";

const CACHE_KEY = "hiremenow.jobs.v1";
const MAX_AGE_MS = 15 * 60_000;

type Region = "india" | "us";
type Snapshot = { scope: string; profile: string; region: Region; filter: StatusFilter; jobs: Job[]; savedAt: number };

export function readJobCache(scope: string | null): Snapshot | null {
  if (!scope) return null;
  try {
    const saved = JSON.parse(sessionStorage.getItem(CACHE_KEY) ?? "null") as Snapshot | null;
    if (saved?.scope === scope && Date.now() - saved.savedAt < MAX_AGE_MS && Array.isArray(saved.jobs)) return saved;
  } catch {
    // Storage may be unavailable. Regular requests still work.
  }
  return null;
}

export function saveJobCache(snapshot: Omit<Snapshot, "savedAt">) {
  try {
    sessionStorage.setItem(CACHE_KEY, JSON.stringify({ ...snapshot, savedAt: Date.now() }));
  } catch {
    clearJobCache();
  }
}

export function clearJobCache() {
  try {
    sessionStorage.removeItem(CACHE_KEY);
  } catch {
    // Storage is optional.
  }
}
