import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";

import MatchFocusForm from "../components/MatchFocusForm";

import {
  apiFetch,
  BACKEND_URL,
  hasVisitorSession,
  type Preferences,
  type UploadResponse,
} from "../lib/api";

export default function SetupPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const resumeRequired = new URLSearchParams(location.search).has("resumeRequired");
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "done" | "error">(
    "idle"
  );
  const [error, setError] = useState<string | null>(null);
  const [skipError, setSkipError] = useState<string | null>(null);
  const [savedResume, setSavedResume] = useState<UploadResponse | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [hasResume, setHasResume] = useState<boolean | null>(null);
  const [preferences, setPreferences] = useState<Preferences | null>(null);
  const [connectionError, setConnectionError] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [skipping, setSkipping] = useState(false);
  const reviewRef = useRef<HTMLElement>(null);
  const uploadStarted = useRef(false);
  const uploadSucceeded = useRef(false);

  const chooseFile = (next: File | null) => {
    if (status === "uploading") return;
    setResult(null);
    if (!next) {
      setFile(null);
      return;
    }
    if (!next.name.toLowerCase().endsWith(".pdf") ||
        (next.type && next.type !== "application/pdf" && next.type !== "application/x-pdf")) {
      setFile(null);
      setError("Choose a PDF file to continue.");
      setStatus("error");
      return;
    }
    if (next.size > 10 * 1024 * 1024) {
      setFile(null);
      setError("Your PDF must be smaller than 10 MB.");
      setStatus("error");
      return;
    }
    setFile(next);
    setError(null);
    setStatus("idle");
  };

  useEffect(() => {
    if (!hasVisitorSession()) {
      setHasResume(false);
      return;
    }
    let cancelled = false;
    Promise.all([
      apiFetch(`${BACKEND_URL}/resumes`),
      apiFetch(`${BACKEND_URL}/preferences`),
    ])
      .then(async ([resumesResponse, preferencesResponse]) => {
        if (!resumesResponse.ok || !preferencesResponse.ok) throw new Error("Could not load your private profile.");
        return [await resumesResponse.json() as UploadResponse[], await preferencesResponse.json() as Preferences] as const;
      })
      .then(([resumes, savedPreferences]) => {
        if (cancelled || uploadSucceeded.current) return;
        setHasResume(resumes.length > 0);
        setSavedResume(resumes[0] ?? null);
        setPreferences(savedPreferences);
      })
      .catch(() => {
        if (!cancelled && !uploadStarted.current) {
          setConnectionError(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const focusInitial = useMemo(() => {
    if (!result) return preferences;
    const suggestedRoles = result.parsed.suggested_target_roles?.length
      ? result.parsed.suggested_target_roles
      : result.parsed.experience.map((job) => job.title).filter(Boolean);
    return {
      target_roles: suggestedRoles,
      seniority: preferences?.seniority ?? null,
      locations: [],
      work_modes: [],
      company_sizes: [],
      needs_visa_sponsorship: false,
      has_saved: false,
      updated_at: null,
    };
  }, [preferences, result]);

  useEffect(() => {
    if (status === "done") reviewRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [status]);

  const skipPreferences = async () => {
    setSkipping(true);
    setSkipError(null);
    try {
      const response = await apiFetch(`${BACKEND_URL}/preferences`, { method: "DELETE" });
      if (!response.ok) throw new Error("Could not skip preferences. Please try again.");
      sessionStorage.removeItem("hiremenow.jobsAutoSearch.india");
      sessionStorage.removeItem("hiremenow.jobsAutoSearch.us");
      navigate("/jobs");
    } catch (cause) {
      setSkipError(cause instanceof Error ? cause.message : "Could not skip preferences.");
    } finally {
      setSkipping(false);
    }
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || status === "uploading") return;

    uploadStarted.current = true;
    setConnectionError(false);
    setStatus("uploading");
    setError(null);
    setResult(null);

    const form = new FormData();
    form.append("file", file);

    try {
      const res = await apiFetch(`${BACKEND_URL}/resumes`, {
        method: "POST",
        body: form,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(typeof body.detail === "string" ? body.detail : `Upload failed (${res.status}). Try again.`);
      }

      const data: UploadResponse = await res.json();
      uploadSucceeded.current = true;
      setResult(data);
      setSavedResume(data);
      setStatus("done");
      setHasResume(true);
      setPreferences(null);
      sessionStorage.removeItem("hiremenow.jobsAutoSearch.india");
      sessionStorage.removeItem("hiremenow.jobsAutoSearch.us");
      setConnectionError(false);
    } catch (err) {
      setError(err instanceof TypeError ? "Couldn’t reach the service. Please try again." :
        err instanceof Error ? err.message : "Upload failed. Please try again.");
      setStatus("error");
    }
  };

  return (
    <div className="flex flex-col gap-8">
      {resumeRequired && !hasResume && <p role="status" className="rounded-xl border border-slate-300 bg-white p-4 text-sm text-slate-800">Please upload your resume and review your details to view Discover Jobs. Preferences are optional.</p>}
      {hasResume && status !== "done" && <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white p-5"><div><strong>Your resume is ready.</strong><p className="mt-1 text-sm text-slate-600">Preferences are optional. You can go straight to your matches.</p></div><Link to="/jobs" className="rounded-lg bg-slate-900 px-5 py-3 text-sm font-bold text-white">Back to matches →</Link></div>}
      <section className="profile-hero">
        <div className="hero-copy">
          <h1>Find your next<br /><span>startup role.</span></h1>
          <p className="hero-description">Match your resume to YC openings, see the skills behind each score, and keep track of the roles worth pursuing.</p>
          <a href="#get-started" className="hero-cta">Start with my resume <span aria-hidden="true">↓</span></a>
        </div>
        <div className="hero-visual">
          <div className="signal-grid" aria-hidden="true"><i /><i /><i /></div>
          <div className="match-blueprint" aria-label="Example job match">
            <div className="blueprint-header"><span>Example match</span><span aria-hidden="true">↗</span></div>
            <div className="blueprint-role">
              <div><h2>Full-Stack Engineer</h2><p>Remote · United States</p></div>
              <span className="blueprint-score">8.4<small>/10</small></span>
            </div>
            <meter aria-label="Example match score" min={0} max={10} value={8.4} />
            <div className="evidence-tags"><span>React</span><span>TypeScript</span><span>APIs</span></div>
          </div>
        </div>
      </section>

      <section id="get-started" className="grid gap-8 rounded-xl border border-[#d6dfd6] bg-white p-5 shadow-[0_20px_60px_-48px_#182523] sm:p-8 lg:grid-cols-[0.8fr_1.2fr] lg:p-10">
        <div>
          <h2 className="display-font text-3xl leading-tight text-[#182523] sm:text-4xl">Start with your resume</h2>
          <p className="mt-4 max-w-sm text-sm leading-7 text-[#4f625d]">Upload a PDF to build your profile. You can review what we extracted before exploring recommendations.</p>
          <div className="mt-8 flex items-start gap-3 rounded-2xl bg-[#edf5e7] p-4 text-sm text-[#4f625d]">
            <span aria-hidden="true" className="text-lg text-[#075e51]">✦</span>
            <span>PDF only, up to 10 MB. No account or signup required.</span>
          </div>
        </div>
        <form onSubmit={onSubmit} className="min-w-0 flex flex-col justify-center gap-3">
          <label
            htmlFor="resume-file"
            onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => { event.preventDefault(); setDragging(false); chooseFile(event.dataTransfer.files[0] ?? null); }}
            className={`flex min-h-44 flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-5 text-center transition focus-within:ring-4 focus-within:ring-[#b0d8b8] ${status === "uploading" ? "cursor-wait" : "cursor-pointer"} ${dragging ? "border-[#075e51] bg-[#e6f3e5]" : "border-[#adc3b1] bg-[#f6faf2] hover:border-[#075e51] hover:bg-[#edf5e7]"}`}
          >
            <span aria-hidden="true" className="grid h-14 w-14 place-items-center rounded-2xl bg-[#deeedb] text-2xl text-[#075e51]">↑</span>
            <span className="mt-3 max-w-full break-all text-lg font-bold text-[#182523]">{file ? file.name : "Choose a PDF or drop it here"}</span>
            {file && <span className="mt-1 text-sm text-[#64748b]">{(file.size / 1024).toFixed(1)} KB{status !== "uploading" && " · Click to change"}</span>}
            <input
              id="resume-file"
              type="file"
              accept=".pdf,application/pdf"
              disabled={status === "uploading"}
              onChange={(event) => chooseFile(event.target.files?.[0] ?? null)}
              className="sr-only"
            />
          </label>
          <button
            type="submit"
            disabled={!file || status === "uploading"}
            className="min-h-12 rounded-xl bg-[#182523] px-5 py-3 text-sm font-bold text-white transition hover:bg-[#075e51] focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-[#075e51] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {status === "uploading" ? "Reading your resume…" : "Analyze my resume"}
          </button>
          {status === "uploading" && <p role="status" className="text-sm text-slate-600">The service may take a moment to start after being idle.</p>}
          {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">{error}</p>}
          {connectionError && <p role="status" className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900">We couldn’t load your saved profile. You can still try uploading a PDF.</p>}
        </form>
      </section>

      {hasResume && focusInitial && (!file || status === "done") && (
        <section ref={reviewRef} className="scroll-mt-24 rounded-xl border border-slate-200 bg-white p-5 sm:p-8">
          <div className="mb-6">
            <p className="text-xs font-bold uppercase tracking-widest text-emerald-800">Your match profile · optional preferences</p>
            <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">Here’s what we picked up from your resume.</h2>
            <p className="mt-2 text-sm text-slate-600">We use your skills and experience to rank YC jobs. Adjust the suggested roles, or skip this step.</p>
            <div className="mt-4 flex flex-wrap gap-2" aria-label="Detected skills">{(result ?? savedResume)?.parsed.skills.slice(0,12).map(skill => <span key={skill} className="rounded-md bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">{skill}</span>)}</div>
          </div>
          <MatchFocusForm initial={focusInitial} submitLabel="Show my matches" onSaved={() => navigate("/jobs")} />
          <button type="button" onClick={skipPreferences} disabled={skipping} className="mt-5 inline-flex min-h-12 items-center rounded-lg border-2 border-slate-800 px-5 py-3 text-sm font-extrabold text-slate-900 hover:bg-slate-100 disabled:opacity-50">
            {skipping ? "Opening jobs…" : "Skip preferences — Show my matches"}
          </button>
          {skipError && <p role="alert" className="mt-3 text-sm text-red-800">{skipError}</p>}
        </section>
      )}

      {result && (
        <details className="rounded-xl border border-[#d6dfd6] bg-white p-5 sm:p-6">
          <summary className="cursor-pointer text-sm font-semibold text-[#075e51]">See what we found in your resume</summary>
          <div className="mt-5"><ParsedView data={result} /></div>
        </details>
      )}
    </div>
  );
}

function ParsedView({ data }: { data: UploadResponse }) {
  const p = data.parsed;
  return (
    <section className="flex flex-col gap-6 rounded-lg border border-zinc-200 bg-white p-6">
      <div className="flex items-baseline justify-between gap-4">
        <h2 className="text-xl font-semibold text-zinc-900">Parsed</h2>
        <span className="text-xs text-zinc-500">
          {data.filename} · resume #{data.id}
        </span>
      </div>

      {(p.contact.name ||
        p.contact.email ||
        p.contact.phone ||
        p.contact.linkedin_url ||
        p.contact.location) && (
        <Field label="Contact">
          <div className="flex flex-col gap-1 text-sm text-zinc-800">
            {p.contact.name && <span>{p.contact.name}</span>}
            {p.contact.email && (
              <span className="text-zinc-600">{p.contact.email}</span>
            )}
            {p.contact.phone && (
              <span className="text-zinc-600">{p.contact.phone}</span>
            )}
            {p.contact.linkedin_url && (
              <a
                href={p.contact.linkedin_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-zinc-600 underline hover:text-zinc-900"
              >
                {p.contact.linkedin_url}
              </a>
            )}
            {p.contact.location && (
              <span className="text-zinc-600">{p.contact.location}</span>
            )}
          </div>
        </Field>
      )}

      {p.summary && (
        <Field label="Summary">
          <p className="text-sm text-zinc-700">{p.summary}</p>
        </Field>
      )}

      {p.years_experience != null && (
        <Field label="Years of experience">
          <span className="text-sm text-zinc-800">{p.years_experience}</span>
        </Field>
      )}

      {p.skills.length > 0 && (
        <Field label="Skills">
          <div className="flex flex-wrap gap-2">
            {p.skills.map((s) => (
              <span
                key={s}
                className="rounded-md bg-zinc-100 px-2 py-0.5 text-xs text-zinc-800"
              >
                {s}
              </span>
            ))}
          </div>
        </Field>
      )}

      {p.experience.length > 0 && (
        <Field label="Experience">
          <ul className="flex flex-col gap-3">
            {p.experience.map((e, i) => (
              <li key={i} className="flex flex-col gap-0.5 text-sm">
                <span className="font-medium text-zinc-900">
                  {e.title}
                  {e.company ? ` · ${e.company}` : ""}
                </span>
                {(e.start || e.end) && (
                  <span className="text-xs text-zinc-500">
                    {e.start ?? "?"} — {e.end ?? "Present"}
                  </span>
                )}
                {e.summary && (
                  <span className="text-zinc-600">{e.summary}</span>
                )}
              </li>
            ))}
          </ul>
        </Field>
      )}

      {p.education.length > 0 && (
        <Field label="Education">
          <ul className="flex flex-col gap-2">
            {p.education.map((e, i) => (
              <li key={i} className="flex flex-col gap-0.5 text-sm">
                <span className="font-medium text-zinc-900">{e.school}</span>
                {(e.degree || e.field) && (
                  <span className="text-zinc-600">
                    {[e.degree, e.field].filter(Boolean).join(", ")}
                    {e.year ? ` · ${e.year}` : ""}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </Field>
      )}
    </section>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">
        {label}
      </span>
      {children}
    </div>
  );
}
