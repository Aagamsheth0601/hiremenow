import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

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
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [hasResume, setHasResume] = useState<boolean | null>(null);
  const [preferences, setPreferences] = useState<Preferences | null>(null);
  const [connectionError, setConnectionError] = useState(false);
  const [dragging, setDragging] = useState(false);

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
        return [await resumesResponse.json() as unknown[], await preferencesResponse.json() as Preferences] as const;
      })
      .then(([resumes, savedPreferences]) => {
        if (cancelled) return;
        setHasResume(resumes.length > 0);
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
      locations: result.parsed.contact.location ? [result.parsed.contact.location] : [],
      work_modes: preferences?.work_modes ?? [],
      company_sizes: preferences?.company_sizes ?? [],
      needs_visa_sponsorship: preferences?.needs_visa_sponsorship ?? false,
      has_saved: preferences?.has_saved ?? false,
      updated_at: preferences?.updated_at ?? null,
    };
  }, [preferences, result]);

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
      setConnectionError(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setStatus("error");
    }
  };

  return (
    <div className="flex flex-col gap-12">
      <section className="grid items-center gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:gap-16">
        <div>
          <span className="inline-flex items-center gap-2 rounded-full border border-[#cce3d0] bg-[#eaf4e9] px-3 py-1.5 text-xs font-bold uppercase tracking-[0.16em] text-[#377454]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#4fa573]" />
            A smarter job search
          </span>
          <h1 className="display-font mt-6 max-w-2xl text-5xl leading-[1.04] text-[#173e35] sm:text-6xl lg:text-7xl">
            Find work that <em className="font-normal text-[#6caa79]">fits</em> the work you&apos;ve done.
          </h1>
          <p className="mt-6 max-w-xl text-base leading-7 text-[#5d7469] sm:text-lg">
            Share your resume, explore relevant openings, and see the reasons behind each match. Your next step starts with a clearer picture of where you belong.
          </p>
          <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3 text-sm font-medium text-[#47745b]">
            <span>✦ Resume-first matching</span>
            <span>✦ Real startup roles</span>
            <span>✦ No account needed</span>
          </div>
          <a href="#get-started" className="mt-8 inline-flex min-h-12 items-center rounded-xl bg-[#173e35] px-6 py-3 text-sm font-bold text-white shadow-[0_12px_25px_-15px_#173e35] transition hover:bg-[#285846] focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-[#4e9b65]">
            Start with my resume <span aria-hidden="true" className="ml-3">↗</span>
          </a>
        </div>

        <div aria-label="Illustration of a sample job match" className="relative mx-auto hidden w-full max-w-lg rounded-[2rem] bg-[#dcebdc] p-5 shadow-[0_28px_70px_-40px_#244738] sm:block sm:p-8">
          <div className="absolute -right-3 -top-4 h-24 w-24 rounded-full border-[16px] border-[#b4d6b5] opacity-60" />
          <div className="relative rounded-[1.5rem] border border-[#dce7dd] bg-white p-6 shadow-[0_18px_40px_-26px_#173e35]">
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs font-bold uppercase tracking-[0.15em] text-[#7a9183]">Your match preview</span>
              <span className="rounded-full bg-[#e7f4e9] px-2.5 py-1 text-xs font-bold text-[#3b8057]">Strong fit</span>
            </div>
            <div className="mt-7 flex items-start gap-3">
              <div className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-[#20473e] text-xl text-white">✳</div>
              <div>
                <p className="text-lg font-bold text-[#173e35]">Full-Stack Engineer</p>
                <p className="mt-0.5 text-sm text-[#759084]">Example startup role · Remote</p>
              </div>
            </div>
            <div className="mt-7 border-t border-[#e7eee8] pt-5">
              <p className="text-xs font-bold uppercase tracking-[0.15em] text-[#7a9183]">Why it fits</p>
              <div className="mt-3 flex flex-wrap gap-2">
                <span className="rounded-full bg-[#eaf4eb] px-3 py-1.5 text-xs font-semibold text-[#417a52]">React</span>
                <span className="rounded-full bg-[#eaf4eb] px-3 py-1.5 text-xs font-semibold text-[#417a52]">TypeScript</span>
                <span className="rounded-full bg-[#eaf4eb] px-3 py-1.5 text-xs font-semibold text-[#417a52]">API development</span>
              </div>
            </div>
          </div>
          <div className="relative mt-5 flex items-center gap-3 rounded-2xl bg-[#20473e] px-5 py-4 text-[#e8f4e7]">
            <span className="text-xl">↗</span>
            <span className="text-sm font-medium">From your experience to your next opportunity.</span>
          </div>
        </div>
      </section>

      <section id="get-started" className="grid gap-8 rounded-[2rem] border border-[#dde8dd] bg-white p-5 shadow-[0_20px_60px_-48px_#173e35] sm:p-8 lg:grid-cols-[0.8fr_1.2fr] lg:p-10">
        <div>
          <span className="text-xs font-bold uppercase tracking-[0.18em] text-[#5a9b6f]">01 / Get started</span>
          <h2 className="display-font mt-4 text-4xl leading-tight text-[#173e35]">Start with your resume.</h2>
          <p className="mt-4 max-w-sm text-sm leading-7 text-[#688075]">Upload a PDF to build your profile. You can review what we extracted before exploring recommendations.</p>
          <div className="mt-8 flex items-start gap-3 rounded-2xl bg-[#f2f7f0] p-4 text-sm text-[#537061]">
            <span aria-hidden="true" className="text-lg text-[#5a9b6f]">✦</span>
            <span>PDF only, up to 10 MB. No account or signup required.</span>
          </div>
        </div>
        <form onSubmit={onSubmit} className="flex flex-col justify-center gap-4">
          <label
            htmlFor="resume-file"
            onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => { event.preventDefault(); setDragging(false); chooseFile(event.dataTransfer.files[0] ?? null); }}
            className={`flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-[1.5rem] border-2 border-dashed px-6 py-8 text-center transition focus-within:ring-4 focus-within:ring-[#a8d5ac] ${dragging ? "border-[#4e9b65] bg-[#eaf5ea]" : "border-[#bdd7c3] bg-[#f8fbf7] hover:border-[#71ae80] hover:bg-[#f2f8f0]"}`}
          >
            <span aria-hidden="true" className="grid h-14 w-14 place-items-center rounded-2xl bg-[#e2f1e3] text-2xl text-[#397850]">↑</span>
            <span className="mt-5 text-lg font-bold text-[#1d4839]">{file ? file.name : "Drop your PDF here"}</span>
            <span className="mt-1 text-sm text-[#789082]">{file ? `${(file.size / 1024).toFixed(1)} KB · Click to change` : "or click to browse your files"}</span>
            <span className="mt-5 rounded-full border border-[#bad8c1] bg-white px-5 py-2 text-sm font-bold text-[#367350]">Choose PDF</span>
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
            className="min-h-12 rounded-xl bg-[#173e35] px-5 py-3 text-sm font-bold text-white transition hover:bg-[#285846] focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-[#4e9b65] disabled:cursor-not-allowed disabled:opacity-50"
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

      {result && <ParsedView data={result} />}

      {hasResume && focusInitial && (
        <section className="rounded-[2rem] border border-[#cce3d0] bg-[#eaf4e9] p-6 shadow-[0_24px_55px_-40px_#173e35] sm:p-8">
          <div className="mb-6 max-w-2xl">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-[#618270]">Your next step</p>
            <h2 className="display-font mt-2 text-3xl text-[#173e35]">Review your match focus</h2>
            <p className="mt-2 text-sm leading-relaxed text-[#537061]">We found a starting point in your resume. Adjust it if you like, or see your matches right away.</p>
          </div>
          <MatchFocusForm initial={focusInitial} submitLabel="Save and discover jobs" onSaved={() => navigate("/jobs")} />
          <Link to="/jobs" className="mt-4 inline-flex min-h-11 items-center text-sm font-semibold text-[#173e35] underline-offset-4 hover:underline">
            Skip for now — discover jobs
          </Link>
        </section>
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
