import type { Job, StatusFilter } from "./api";

const CACHE_KEY = "hiremenow.jobs.v2";
const MAX_AGE_MS = 24 * 60 * 60_000;

type Region = "india" | "us";
type Snapshot = { scope: string; profile: string; region: Region; filter: StatusFilter; jobs: Job[]; savedAt: number };

export function readJobCache(scope: string | null): Snapshot | null {
  if (!scope) return null;
  try {
    const saved = JSON.parse(localStorage.getItem(CACHE_KEY) ?? "null") as Snapshot | null;
    if (saved?.scope === scope && Array.isArray(saved.jobs)) {
      const age = Date.now() - saved.savedAt;
      if (age >= 0 && age < MAX_AGE_MS) return saved;
    }
  } catch {
    // Storage may be unavailable. Regular requests still work.
  }
  return null;
}

export function saveJobCache(snapshot: Omit<Snapshot, "savedAt">) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ ...snapshot, savedAt: Date.now() }));
  } catch {
    clearJobCache();
  }
}

export function updateJobCache(
  scope: string | null,
  profile: string,
  region: Region,
  filter: StatusFilter,
  update: (jobs: Job[]) => Job[],
) {
  const snapshot = readJobCache(scope);
  if (snapshot?.profile !== profile || snapshot.region !== region || snapshot.filter !== filter) return;
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ ...snapshot, jobs: update(snapshot.jobs) }));
  } catch {
    clearJobCache();
  }
}

export function clearJobCache() {
  try {
    localStorage.removeItem(CACHE_KEY);
  } catch {
    // Storage is optional.
  }
}
