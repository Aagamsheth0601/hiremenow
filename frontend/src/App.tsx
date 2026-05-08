import { useState } from "react";

const BACKEND_URL =
  import.meta.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000";

type Experience = {
  title: string;
  company: string;
  start?: string | null;
  end?: string | null;
  summary?: string | null;
};

type Education = {
  school: string;
  degree?: string | null;
  field?: string | null;
  year?: string | null;
};

type ParsedResume = {
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

type UploadResponse = {
  id: number;
  filename: string;
  uploaded_at: string;
  parsed: ParsedResume;
};

export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "done" | "error">(
    "idle"
  );
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);

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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setStatus("error");
    }
  };

  return (
    <div className="min-h-screen w-full bg-zinc-50 px-6 py-16">
      <main className="mx-auto flex w-full max-w-2xl flex-col gap-8">
        <header className="flex flex-col gap-2">
          <h1 className="text-3xl font-semibold tracking-tight text-zinc-900">
            hiremenow
          </h1>
          <p className="text-zinc-600">
            Upload your resume (PDF) to get started.
          </p>
        </header>

        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-2">
            <span className="text-sm font-medium text-zinc-800">
              Resume PDF
            </span>
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
      </main>
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
