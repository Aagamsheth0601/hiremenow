import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, Link } from "react-router-dom";

import MatchFocusForm from "../components/MatchFocusForm";

import {
  apiFetch,
  BACKEND_URL,
  type Preferences,
  type UploadResponse,
} from "../lib/api";

export default function SetupPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "done" | "error">(
    "idle"
  );
  const [error, setError] = useState<string | null>(null);
  const [savedResume, setSavedResume] = useState<UploadResponse | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [hasResume, setHasResume] = useState<boolean | null>(null);
  const [preferences, setPreferences] = useState<Preferences | null>(null);
  const [connectionError, setConnectionError] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [skipping, setSkipping] = useState(false);
  const reviewRef = useRef<HTMLElement>(null);

  const chooseFile = (next: File | null) => {
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
        if (cancelled) return;
        setHasResume(resumes.length > 0);
        setSavedResume(resumes[0] ?? null);
        setPreferences(savedPreferences);
      })
      .catch(() => {
        if (!cancelled) {
          setHasResume(false);
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
    setError(null);
    try {
      const response = await apiFetch(`${BACKEND_URL}/preferences`, { method: "DELETE" });
      if (!response.ok) throw new Error("Could not skip preferences. Please try again.");
      sessionStorage.removeItem("hiremenow.jobsAutoSearch.india");
      sessionStorage.removeItem("hiremenow.jobsAutoSearch.us");
      navigate("/jobs");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not skip preferences.");
    } finally {
      setSkipping(false);
    }
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

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
        throw new Error(body.detail ?? `Upload failed (${res.status})`);
      }

      const data: UploadResponse = await res.json();
      setResult(data);
      setStatus("done");
      setHasResume(true);
      setPreferences(null);
      sessionStorage.removeItem("hiremenow.jobsAutoSearch.india");
      sessionStorage.removeItem("hiremenow.jobsAutoSearch.us");
      setConnectionError(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setStatus("error");
    }
  };

  return (
    <div className="flex flex-col gap-8">
      {hasResume && status !== "done" && <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-200 bg-white p-5"><div><strong>Your resume is ready.</strong><p className="mt-1 text-sm text-slate-600">Preferences are optional. You can go straight to your matches.</p></div><Link to="/jobs" className="rounded-lg bg-slate-900 px-5 py-3 text-sm font-bold text-white">Back to matches →</Link></div>}
      <section className="profile-hero">
        <div className="hero-copy">
          <p className="eyebrow">YOUR NEXT MOVE / POWERED BY YOUR EXPERIENCE</p>
          <h1>Less searching.<br /><span>More right fits.</span></h1>
          <p className="hero-description">Turn your resume into a focused shortlist of YC startup jobs. Understand each match, track your applications, and prepare your next conversation.</p>
          <a href="#get-started" className="hero-cta">Build my match profile <span aria-hidden="true">↗</span></a>
          <p className="hero-caption">No signup. Optional preferences. You stay in control.</p>
        </div>
        <div className="match-blueprint" aria-label="Illustrative match preview">
          <div className="blueprint-header"><span>MATCH BREAKDOWN</span><span className="sample-badge">EXAMPLE</span></div>
          <div className="blueprint-role"><span className="company-mark" aria-hidden="true">↗</span><div><h2>Full-Stack Engineer</h2><p>Example startup · United States</p></div></div>
          <div className="evidence-line"><span>01</span><div><strong>Your experience</strong><p>Building web applications and APIs</p></div></div>
          <div className="evidence-line"><span>02</span><div><strong>Skills in common</strong><div className="evidence-tags"><span>React</span><span>TypeScript</span><span>APIs</span></div></div></div>
          <div className="evidence-line"><span>03</span><div><strong>Your next step</strong><p>Review the role. Save it. Make your move.</p></div></div>
          <div className="blueprint-footer">See the evidence behind the match <span aria-hidden="true">→</span></div>
        </div>
      </section>
      <div className="workflow-strip" aria-label="How it works"><div><span>01</span><strong>Build your profile</strong><p>Start with your resume</p></div><div><span>02</span><strong>Find your fit</strong><p>Compare roles and match evidence</p></div><div><span>03</span><strong>Make your move</strong><p>Track progress and draft outreach</p></div></div>

      <section id="get-started" className="grid gap-8 rounded-xl border border-[#dce2ec] bg-white p-5 shadow-[0_20px_60px_-48px_#172b4d] sm:p-8 lg:grid-cols-[0.8fr_1.2fr] lg:p-10">
        <div>
          <span className="text-xs font-bold uppercase tracking-[0.18em] text-[#3859cf]">01 / Get started</span>
          <h2 className="display-font mt-4 text-4xl leading-tight text-[#172b4d]">Start with your resume.</h2>
          <p className="mt-4 max-w-sm text-sm leading-7 text-[#596980]">Upload a PDF to build your profile. You can review what we extracted before exploring recommendations.</p>
          <div className="mt-8 flex items-start gap-3 rounded-2xl bg-[#f1f5ff] p-4 text-sm text-[#596980]">
            <span aria-hidden="true" className="text-lg text-[#3859cf]">✦</span>
            <span>PDF only, up to 10 MB. No account or signup required.</span>
          </div>
        </div>
        <form onSubmit={onSubmit} className="flex flex-col justify-center gap-4">
          <label
            htmlFor="resume-file"
            onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => { event.preventDefault(); setDragging(false); chooseFile(event.dataTransfer.files[0] ?? null); }}
            className={`flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-8 text-center transition focus-within:ring-4 focus-within:ring-[#c7d2fe] ${dragging ? "border-[#3859cf] bg-[#eef2ff]" : "border-[#b9c8e1] bg-[#f7f9fd] hover:border-[#3859cf] hover:bg-[#f1f5ff]"}`}
          >
            <span aria-hidden="true" className="grid h-14 w-14 place-items-center rounded-2xl bg-[#e8edff] text-2xl text-[#3859cf]">↑</span>
            <span className="mt-5 text-lg font-bold text-[#172b4d]">{file ? file.name : "Drop your PDF here"}</span>
            <span className="mt-1 text-sm text-[#64748b]">{file ? `${(file.size / 1024).toFixed(1)} KB · Click to change` : "or click to browse your files"}</span>
            <span className="mt-5 rounded-full border border-[#b9c8e1] bg-white px-5 py-2 text-sm font-bold text-[#3859cf]">Choose PDF</span>
            <input
              id="resume-file"
              type="file"
              accept=".pdf,application/pdf"
              onChange={(event) => chooseFile(event.target.files?.[0] ?? null)}
              className="sr-only"
            />
          </label>
          <button
            type="submit"
            disabled={!file || status === "uploading"}
            className="min-h-12 rounded-xl bg-[#172b4d] px-5 py-3 text-sm font-bold text-white transition hover:bg-[#274fc5] focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-[#3859cf] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {status === "uploading" ? "Reading your resume…" : "Analyze my resume"}
          </button>
        </form>
      </section>

      {error && (
        <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {connectionError && (
        <div role="alert" className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          The recommendation service is unavailable right now. You can explore this page, but uploading a resume requires the service to be running.
        </div>
      )}

      {hasResume && focusInitial && (!file || status === "done") && (
        <section ref={reviewRef} className="scroll-mt-24 rounded-xl border border-slate-200 bg-white p-5 sm:p-8">
          <div className="mb-6">
            <p className="text-xs font-bold uppercase tracking-widest text-indigo-700">Your match profile · optional preferences</p>
            <h2 className="mt-2 text-2xl font-bold tracking-tight text-slate-900">Here’s what we picked up from your resume.</h2>
            <p className="mt-2 text-sm text-slate-600">We use your skills and experience to rank YC jobs. Adjust the suggested roles, or skip this step.</p>
            <div className="mt-4 flex flex-wrap gap-2" aria-label="Detected skills">{(result ?? savedResume)?.parsed.skills.slice(0,12).map(skill => <span key={skill} className="rounded-md bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">{skill}</span>)}</div>
          </div>
          <MatchFocusForm initial={focusInitial} submitLabel="Show my matches" onSaved={() => navigate("/jobs")} />
          <button type="button" onClick={skipPreferences} disabled={skipping} className="mt-5 inline-flex min-h-12 items-center rounded-lg border-2 border-slate-800 px-5 py-3 text-sm font-extrabold text-slate-900 hover:bg-slate-100 disabled:opacity-50">
            {skipping ? "Opening jobs…" : "Skip preferences — Show my matches"}
          </button>
        </section>
      )}

      {result && (
        <details className="rounded-xl border border-[#dce2ec] bg-white p-5 sm:p-6">
          <summary className="cursor-pointer text-sm font-semibold text-[#274fc5]">See what we found in your resume</summary>
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
