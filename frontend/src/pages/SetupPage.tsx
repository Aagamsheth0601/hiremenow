import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  BACKEND_URL,
  type Preferences,
  type UploadResponse,
} from "../lib/api";

const SENIORITY_OPTIONS = ["intern", "junior", "mid", "senior", "staff+"];
const WORK_MODE_OPTIONS = [
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Hybrid" },
  { value: "on-site", label: "On-site" },
];
const COMPANY_SIZE_OPTIONS = [
  { value: "startup", label: "Startup" },
  { value: "mid-size", label: "Mid-size" },
  { value: "large-mnc", label: "Large / MNC" },
];

export default function SetupPage() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "done" | "error">(
    "idle"
  );
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [hasResume, setHasResume] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${BACKEND_URL}/resumes`)
      .then((res) => (res.ok ? res.json() : []))
      .then((rows: unknown[]) => {
        if (!cancelled) setHasResume(rows.length > 0);
      })
      .catch(() => {
        if (!cancelled) setHasResume(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setStatus("uploading");
    setError(null);
    setResult(null);

    const form = new FormData();
    form.append("file", file);

    try {
      const res = await fetch(`${BACKEND_URL}/resumes`, {
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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setStatus("error");
    }
  };

  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold tracking-tight text-zinc-900">
          Setup
        </h1>
        <p className="text-zinc-600">
          Upload your resume to get started — it's used to match jobs and gets
          attached to outreach emails. Preferences below pre-fill from the
          resume; tweak anything that's wrong.
        </p>
      </header>

      <form onSubmit={onSubmit} className="flex flex-col gap-4">
        <label className="flex flex-col gap-2">
          <span className="text-sm font-medium text-zinc-800">Resume PDF</span>
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-zinc-700 file:mr-4 file:rounded-md file:border-0 file:bg-zinc-900 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-zinc-700"
          />
          {file && (
            <span className="text-xs text-zinc-500">
              {file.name} — {(file.size / 1024).toFixed(1)} KB
            </span>
          )}
        </label>

        <button
          type="submit"
          disabled={!file || status === "uploading"}
          className="self-start rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {status === "uploading" ? "Parsing…" : "Upload & parse"}
        </button>
      </form>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && <ParsedView data={result} />}

      {hasResume === false ? (
        <section className="rounded-lg border border-dashed border-zinc-300 bg-white p-8 text-center">
          <p className="text-sm font-medium text-zinc-700">
            Preferences locked.
          </p>
          <p className="mt-2 text-xs text-zinc-500">
            Upload a resume above to unlock the preferences form.
          </p>
        </section>
      ) : (
        <PreferencesForm refreshKey={result?.id ?? 0} />
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

function PreferencesForm({ refreshKey }: { refreshKey: number }) {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const [rolesInput, setRolesInput] = useState("");
  const [seniority, setSeniority] = useState<string>("");
  const [locationsInput, setLocationsInput] = useState("");
  const [workModes, setWorkModes] = useState<string[]>([]);
  const [companySizes, setCompanySizes] = useState<string[]>([]);
  const [needsVisa, setNeedsVisa] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch(`${BACKEND_URL}/preferences`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`Load failed (${res.status})`);
        return (await res.json()) as Preferences;
      })
      .then((p) => {
        if (cancelled) return;
        setRolesInput(p.target_roles.join(", "));
        setSeniority(p.seniority ?? "");
        setLocationsInput(p.locations.join(", "));
        setWorkModes(p.work_modes);
        setCompanySizes(p.company_sizes);
        setNeedsVisa(p.needs_visa_sponsorship);
        setSavedAt(p.has_saved ? p.updated_at : null);
      })
      .catch((err) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Load failed");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  const splitCsv = (s: string) =>
    s
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);

  const toggle = (list: string[], value: string) =>
    list.includes(value) ? list.filter((v) => v !== value) : [...list, value];

  const onSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      const res = await fetch(`${BACKEND_URL}/preferences`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_roles: splitCsv(rolesInput),
          seniority: seniority || null,
          locations: splitCsv(locationsInput),
          work_modes: workModes,
          company_sizes: companySizes,
          needs_visa_sponsorship: needsVisa,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `Save failed (${res.status})`);
      }
      const p: Preferences = await res.json();
      setSavedAt(p.updated_at);
      navigate("/jobs");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="flex flex-col gap-6 rounded-lg border border-zinc-200 bg-white p-6">
      <div className="flex items-baseline justify-between gap-4">
        <h2 className="text-xl font-semibold text-zinc-900">Preferences</h2>
        {savedAt && (
          <span className="text-xs text-zinc-500">
            Saved {new Date(savedAt).toLocaleString()}
          </span>
        )}
      </div>

      {loading ? (
        <p className="text-sm text-zinc-500">Loading…</p>
      ) : (
        <form onSubmit={onSave} className="flex flex-col gap-5">
          <Field label="Target roles (comma-separated)">
            <input
              type="text"
              value={rolesInput}
              onChange={(e) => setRolesInput(e.target.value)}
              placeholder="Software Engineer, ML Engineer"
              className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-900 focus:outline-none"
            />
          </Field>

          <Field label="Seniority">
            <select
              value={seniority}
              onChange={(e) => setSeniority(e.target.value)}
              className="w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm focus:border-zinc-900 focus:outline-none"
            >
              <option value="">— select —</option>
              {SENIORITY_OPTIONS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Locations (comma-separated)">
            <input
              type="text"
              value={locationsInput}
              onChange={(e) => setLocationsInput(e.target.value)}
              placeholder="San Francisco, New York, Remote"
              className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm focus:border-zinc-900 focus:outline-none"
            />
          </Field>

          <Field label="Work mode (multi-select; empty = no preference)">
            <div className="flex flex-wrap gap-2">
              {WORK_MODE_OPTIONS.map((opt) => {
                const active = workModes.includes(opt.value);
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setWorkModes(toggle(workModes, opt.value))}
                    className={`rounded-md border px-3 py-1.5 text-sm transition ${
                      active
                        ? "border-zinc-900 bg-zinc-900 text-white"
                        : "border-zinc-300 bg-white text-zinc-700 hover:border-zinc-500"
                    }`}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </Field>

          <Field label="Company size">
            <div className="flex flex-wrap gap-2">
              {COMPANY_SIZE_OPTIONS.map((opt) => {
                const active = companySizes.includes(opt.value);
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() =>
                      setCompanySizes(toggle(companySizes, opt.value))
                    }
                    className={`rounded-md border px-3 py-1.5 text-sm transition ${
                      active
                        ? "border-zinc-900 bg-zinc-900 text-white"
                        : "border-zinc-300 bg-white text-zinc-700 hover:border-zinc-500"
                    }`}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </Field>

          <label className="flex items-center gap-2 text-sm text-zinc-800">
            <input
              type="checkbox"
              checked={needsVisa}
              onChange={(e) => setNeedsVisa(e.target.checked)}
              className="h-4 w-4 rounded border-zinc-300"
            />
            Needs visa sponsorship
          </label>

          {error && (
            <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={saving}
            className="self-start rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save preferences"}
          </button>
        </form>
      )}
    </section>
  );
}
