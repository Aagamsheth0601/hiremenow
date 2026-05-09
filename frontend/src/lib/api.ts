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
