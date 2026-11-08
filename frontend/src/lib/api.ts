export const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";

const TOKEN_KEY = "hiremenow.visitorToken.v2";
let tokenPromise: Promise<string> | null = null;

export function hasVisitorSession(): boolean {
  return Boolean(localStorage.getItem(TOKEN_KEY));
}

// Bound network waits so a sleeping or unreachable API cannot leave the UI
// spinning indefinitely. Parsing and drafting have a longer model-call budget.
async function timedFetch(url: string, init: RequestInit = {}): Promise<Response> {
  const slowAction = init.method === "POST" &&
    (/\/resumes(?:\/latest\/reparse)?$/.test(url) || /\/draft(?:\?|$)/.test(url));
  const controller = new AbortController();
  const abort = () => controller.abort();
  init.signal?.addEventListener("abort", abort, { once: true });
  if (init.signal?.aborted) abort();
  const timer = window.setTimeout(abort, slowAction ? 90000 : 30000);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (error) {
    if (controller.signal.aborted) {
      throw new Error("The server took too long to respond. Please try again shortly.");
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
    init.signal?.removeEventListener("abort", abort);
  }
}

async function visitorToken(): Promise<string> {
  const saved = localStorage.getItem(TOKEN_KEY);
  if (saved) return saved;
  if (!tokenPromise) {
    tokenPromise = timedFetch(`${BACKEND_URL}/sessions`, { method: "POST" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Could not start a private browser session.");
        const data = (await response.json()) as { token: string };
        localStorage.setItem(TOKEN_KEY, data.token);
        return data.token;
      })
      .finally(() => { tokenPromise = null; });
  }
  return tokenPromise;
}

export async function apiFetch(url: string, init: RequestInit = {}): Promise<Response> {
  const token = await visitorToken();
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
  const response = await timedFetch(url, { ...init, headers });
  if (response.status !== 401) return response;

  // The server may have started with a new database. Create a fresh session.
  localStorage.removeItem(TOKEN_KEY);
  const newToken = await visitorToken();
  headers.set("Authorization", `Bearer ${newToken}`);
  return timedFetch(url, { ...init, headers });
}

export type Experience = {
  title: string;
  company: string;
  start?: string | null;
  end?: string | null;
  summary?: string | null;
};

export type Education = {
  school: string;
  degree?: string | null;
  field?: string | null;
  year?: string | null;
};

export type ParsedResume = {
  contact: {
    name?: string | null;
    email?: string | null;
    phone?: string | null;
    linkedin_url?: string | null;
    location?: string | null;
  };
  summary?: string | null;
  skills: string[];
  experience: Experience[];
  education: Education[];
  years_experience?: number | null;
  suggested_target_roles?: string[];
};

export type UploadResponse = {
  id: number;
  filename: string;
  uploaded_at: string;
  parsed: ParsedResume;
};

export type Preferences = {
  target_roles: string[];
  seniority: string | null;
  locations: string[];
  work_modes: string[];
  company_sizes: string[];
  needs_visa_sponsorship: boolean;
  has_saved: boolean;
  updated_at: string | null;
};

export type ApplicationStatus =
  | "reached_out"
  | "applied"
  | "replied"
  | "rejected";

export type StatusFilter = "active" | ApplicationStatus | "starred" | "all";

export type Job = {
  id: number;
  title: string;
  description: string;
  company_name: string;
  company_one_liner: string | null;
  company_industry: string | null;
  company_stage: string | null;
  company_batch: string | null;
  company_website: string | null;
  locations: string[];
  tags: string[];
  founders: Founder[];
  contact_emails: string[];
  application_status: ApplicationStatus | null;
  status_updated_at: string | null;
  is_starred: boolean;
  draft_kinds: string[];
  source_url: string;
  scraped_at: string;
  last_checked_at?: string;
  match_score?: number;
  match_details?: {
    matched_skills: string[];
    missing_skills: string[];
    matched_target_roles: string[];
    skill_coverage: number;
    role_in_title: boolean;
  };
};

export type StatusCounts = Record<StatusFilter, number>;

export type ScrapeResult = {
  companies_visited: number;
  jobs_seen: number;
  jobs_inserted: number;
  jobs_updated: number;
  errors: number;
  total_jobs_in_db: number;
};

export type Founder = {
  name: string;
  linkedin_url: string;
  twitter_url: string | null;
};

export type EmailDraft = {
  kind: "email";
  subject: string;
  body: string;
  recipients: string[];
  founders: Founder[];
};

export type LinkedInDraft = {
  kind: "linkedin";
  message: string;
  founders: Founder[];
};

export type OutreachDraft = EmailDraft | LinkedInDraft;
