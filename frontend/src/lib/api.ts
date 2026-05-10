export const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";

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
  match_score?: number;
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
