import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  BACKEND_URL,
  type EmailDraft,
  type Job,
  type LinkedInDraft,
  type Preferences,
  type ScrapeResult,
} from "../lib/api";

type DraftKind = "email" | "linkedin";
type DraftState =
  | { status: "idle" }
  | { status: "loading"; kind: DraftKind }
  | { status: "ready"; kind: DraftKind; draft: EmailDraft | LinkedInDraft }
  | { status: "error"; kind: DraftKind; message: string };

function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  const diff = Math.max(0, Date.now() - then);
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m} min ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} hr ago`;
  const d = Math.floor(h / 24);
  return `${d} day${d === 1 ? "" : "s"} ago`;
}

export default function JobsPage() {
  const [prefs, setPrefs] = useState<Preferences | null>(null);
  const [prefsLoading, setPrefsLoading] = useState(true);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [jobsLoading, setJobsLoading] = useState(true);
  const [scraping, setScraping] = useState(false);
  const [scrapeMsg, setScrapeMsg] = useState<string | null>(null);
  const [scrapeError, setScrapeError] = useState<string | null>(null);
  const [region, setRegion] = useState<"india" | "us">("india");

  const loadJobs = useCallback(async (regionParam: "india" | "us") => {
    setJobsLoading(true);
    try {
      const res = await fetch(
        `${BACKEND_URL}/jobs?limit=200&region=${regionParam}`,
      );
      if (!res.ok) throw new Error(`status ${res.status}`);
      const data: Job[] = await res.json();
      setJobs(data);
    } catch (err) {
      console.error("failed to load jobs", err);
    } finally {
      setJobsLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetch(`${BACKEND_URL}/preferences`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!cancelled) setPrefs(data);
      })
      .finally(() => {
        if (!cancelled) setPrefsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    loadJobs(region);
  }, [loadJobs, region]);

  const lastScrapedLabel = useMemo(() => {
    if (jobs.length === 0) return null;
    const newest = jobs.reduce((acc, j) =>
      new Date(j.scraped_at).getTime() > new Date(acc.scraped_at).getTime() ? j : acc,
    );
    return timeAgo(newest.scraped_at);
  }, [jobs]);

  const handleScrape = async () => {
    setScraping(true);
    setScrapeMsg(null);
    setScrapeError(null);
    try {
      const res = await fetch(
        `${BACKEND_URL}/jobs/scrape?company_limit=25&job_limit_per_company=5&region=${region}`,
        { method: "POST" },
      );
      if (!res.ok) throw new Error(`status ${res.status}`);
      const data: ScrapeResult = await res.json();
      const regionLabel = region === "india" ? "India" : "US";
      setScrapeMsg(
        `Scraped ${data.companies_visited} ${regionLabel} companies — ${data.jobs_inserted} new, ${data.jobs_updated} updated (total ${data.total_jobs_in_db}).`,
      );
      await loadJobs(region);
    } catch (err) {
      console.error("scrape failed", err);
      setScrapeError(err instanceof Error ? err.message : "scrape failed");
    } finally {
      setScraping(false);
    }
  };

  if (prefsLoading) {
    return (
      <div className="rounded-lg border border-dashed border-zinc-300 bg-white p-10 text-center text-sm text-zinc-500">
        Loading…
      </div>
    );
  }

  if (!prefs?.has_saved) {
    return (
      <div className="rounded-lg border border-dashed border-zinc-300 bg-white p-10 text-center">
        <p className="text-sm font-medium text-zinc-700">
          Save your preferences first.
        </p>
        <p className="mt-2 text-xs text-zinc-500">
          Head to{" "}
          <Link to="/" className="text-zinc-900 underline hover:text-zinc-700">
            Setup
          </Link>{" "}
          and save your preferences — matched jobs will populate here.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-3">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="flex flex-col gap-1">
            <h1 className="text-3xl font-semibold tracking-tight text-zinc-900">
              Jobs
            </h1>
            <p className="text-sm text-zinc-600">
              {jobsLoading
                ? "Loading jobs…"
                : `${jobs.length} ${jobs.length === 1 ? "job" : "jobs"}${
                    lastScrapedLabel ? ` · last scraped ${lastScrapedLabel}` : ""
                  }`}
            </p>
            <p className="text-xs text-zinc-500">
              Sorted by match score (out of 10) — overlap of job title and
              description with your resume skills and saved target roles.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={region}
              onChange={(e) => setRegion(e.target.value as "india" | "us")}
              disabled={scraping}
              className="rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 disabled:cursor-not-allowed disabled:bg-zinc-100"
            >
              <option value="india">India</option>
              <option value="us">US</option>
            </select>
            <button
              type="button"
              onClick={handleScrape}
              disabled={scraping}
              className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:bg-zinc-400"
            >
              {scraping ? "Scraping…" : "Scrape now"}
            </button>
          </div>
        </div>
        {scrapeMsg && (
          <p className="rounded-md bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
            {scrapeMsg}
          </p>
        )}
        {scrapeError && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">
            Scrape failed: {scrapeError}
          </p>
        )}
      </header>

      <p className="text-xs text-zinc-500">
        Drafts are AI-generated and never sent automatically — copy & review
        before pasting into your email or LinkedIn.
      </p>

      {jobsLoading ? (
        <div className="rounded-lg border border-dashed border-zinc-300 bg-white p-10 text-center text-sm text-zinc-500">
          Loading jobs…
        </div>
      ) : jobs.length === 0 ? (
        <div className="rounded-lg border border-dashed border-zinc-300 bg-white p-10 text-center">
          <p className="text-sm font-medium text-zinc-700">No jobs yet.</p>
          <p className="mt-2 text-xs text-zinc-500">
            Hit “Scrape now” to pull the latest YC openings.
          </p>
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {jobs.map((job) => (
            <JobCard key={job.id} job={job} />
          ))}
        </ul>
      )}
    </div>
  );
}

function GmailIcon({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <path
        d="M22 6.27v11.46c0 .69-.56 1.27-1.25 1.27H18V9.83l-6 4.5-6-4.5V19H3.25C2.56 19 2 18.42 2 17.73V6.27c0-.69.56-1.27 1.25-1.27H4l8 6 8-6h.75c.69 0 1.25.58 1.25 1.27z"
        fill="#EA4335"
      />
    </svg>
  );
}

function LinkedInIcon({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <path
        d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"
        fill="#0A66C2"
      />
    </svg>
  );
}

function gmailComposeUrl(
  recipients: string[],
  subject: string,
  body: string,
): string {
  const params = new URLSearchParams({
    view: "cm",
    fs: "1",
    su: subject,
    body,
  });
  if (recipients.length > 0) {
    params.set("to", recipients.join(","));
  }
  return `https://mail.google.com/mail/?${params.toString()}`;
}

function JobCard({ job: initialJob }: { job: Job }) {
  const [job, setJob] = useState(initialJob);
  const [draft, setDraft] = useState<DraftState>({ status: "idle" });
  const [copied, setCopied] = useState<"subject" | "body" | "message" | null>(null);
  const [enriching, setEnriching] = useState(false);

  const enrich = async () => {
    setEnriching(true);
    try {
      const res = await fetch(`${BACKEND_URL}/jobs/${job.id}/enrich`, {
        method: "POST",
      });
      if (!res.ok) return;
      const data: { founders: typeof job.founders; contact_emails: string[] } =
        await res.json();
      setJob({
        ...job,
        founders: data.founders,
        contact_emails: data.contact_emails,
      });
    } catch (err) {
      console.error("enrich failed", err);
    } finally {
      setEnriching(false);
    }
  };

  const generate = async (kind: DraftKind) => {
    setDraft({ status: "loading", kind });
    setCopied(null);
    try {
      const res = await fetch(
        `${BACKEND_URL}/jobs/${job.id}/draft?kind=${kind}`,
        { method: "POST" },
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `Draft failed (${res.status})`);
      }
      const data = (await res.json()) as EmailDraft | LinkedInDraft;
      setDraft({ status: "ready", kind, draft: data });
    } catch (err) {
      setDraft({
        status: "error",
        kind,
        message: err instanceof Error ? err.message : "Draft failed",
      });
    }
  };

  const copy = async (text: string, label: "subject" | "body" | "message") => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(label);
      setTimeout(() => setCopied(null), 1500);
    } catch (err) {
      console.error("clipboard write failed", err);
    }
  };

  const openGmail = () => {
    if (draft.status !== "ready" || draft.draft.kind !== "email") return;
    window.open(
      gmailComposeUrl(
        draft.draft.recipients,
        draft.draft.subject,
        draft.draft.body,
      ),
      "_blank",
      "noopener,noreferrer",
    );
  };

  return (
    <li className="group rounded-lg border border-zinc-200 bg-white p-4 shadow-sm transition hover:border-zinc-300 hover:shadow-md">
      <div className="flex items-start gap-4">
        <div className="flex flex-1 flex-col gap-1">
          <div className="flex flex-wrap items-center gap-2">
            <a
              href={job.source_url}
              target="_blank"
              rel="noreferrer"
              className="text-base font-semibold text-zinc-900 hover:underline"
            >
              {job.title}
            </a>
            {job.match_score !== undefined && (
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  job.match_score >= 7
                    ? "bg-emerald-100 text-emerald-800"
                    : job.match_score >= 4
                    ? "bg-amber-50 text-amber-800"
                    : "bg-zinc-100 text-zinc-700"
                }`}
                title="Match score out of 10 — overlap between job title/description and your resume skills + saved target roles."
              >
                {job.match_score}/10
              </span>
            )}
          </div>
          <p className="text-sm text-zinc-700">
            <span className="font-medium text-zinc-900">{job.company_name}</span>
            {job.company_batch ? ` · ${job.company_batch}` : ""}
            {job.company_stage ? ` · ${job.company_stage}` : ""}
            {job.company_industry ? ` · ${job.company_industry}` : ""}
          </p>
          {job.company_one_liner && (
            <p className="text-sm text-zinc-500">{job.company_one_liner}</p>
          )}

          {(job.locations.length > 0 || job.tags.length > 0) && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {job.locations.map((loc) => (
                <span
                  key={`loc-${loc}`}
                  className="rounded-full bg-zinc-100 px-2 py-0.5 text-xs text-zinc-700"
                >
                  {loc}
                </span>
              ))}
              {job.tags.slice(0, 6).map((tag) => (
                <span
                  key={`tag-${tag}`}
                  className="rounded-full border border-zinc-200 px-2 py-0.5 text-xs text-zinc-500"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          {job.founders.length > 0 ? (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                Founders
              </span>
              {job.founders.map((f) => (
                <a
                  key={f.linkedin_url}
                  href={f.linkedin_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-full border border-zinc-200 bg-white px-2.5 py-1 text-xs text-zinc-800 hover:border-[#0A66C2] hover:text-[#0A66C2]"
                  title={`Open ${f.name} on LinkedIn`}
                >
                  <LinkedInIcon className="h-3.5 w-3.5" />
                  {f.name}
                </a>
              ))}
            </div>
          ) : (
            <div className="mt-3">
              <button
                type="button"
                onClick={enrich}
                disabled={enriching}
                className="text-xs text-zinc-500 underline hover:text-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {enriching ? "Finding founders…" : "Find founders & emails"}
              </button>
            </div>
          )}

          {job.contact_emails.length > 0 && (
            <p className="mt-1 text-xs text-zinc-500">
              <span className="font-medium uppercase tracking-wide">Emails:</span>{" "}
              {job.contact_emails.join(", ")}
            </p>
          )}
        </div>

        <div className="flex flex-col items-end gap-2">
          <span className="text-xs text-zinc-400">
            {timeAgo(job.scraped_at)}
          </span>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => generate("email")}
              disabled={draft.status === "loading"}
              title="Draft & open in Gmail"
              className="rounded-md border border-zinc-200 p-1.5 transition hover:border-zinc-400 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {draft.status === "loading" && draft.kind === "email" ? (
                <span className="block h-5 w-5 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-700" />
              ) : (
                <GmailIcon className="h-5 w-5" />
              )}
            </button>
            <button
              type="button"
              onClick={() => generate("linkedin")}
              disabled={draft.status === "loading"}
              title="Draft & open LinkedIn"
              className="rounded-md border border-zinc-200 p-1.5 transition hover:border-zinc-400 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {draft.status === "loading" && draft.kind === "linkedin" ? (
                <span className="block h-5 w-5 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-700" />
              ) : (
                <LinkedInIcon className="h-5 w-5" />
              )}
            </button>
          </div>
        </div>
      </div>

      {draft.status === "error" && (
        <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">
          {draft.message}
        </p>
      )}

      {draft.status === "ready" && draft.draft.kind === "email" && (
        <div className="mt-4 flex flex-col gap-3 rounded-md border border-zinc-200 bg-zinc-50 p-3">
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">
              Recipients
            </span>
            {draft.draft.recipients.length > 0 ? (
              <p className="text-sm text-zinc-900">
                {draft.draft.recipients.join(", ")}
              </p>
            ) : (
              <p className="text-sm text-amber-700">
                None found — fill the To field manually after Gmail opens.
              </p>
            )}
          </div>

          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                Subject
              </span>
              <button
                type="button"
                onClick={() => copy(draft.draft.subject, "subject")}
                className="text-xs text-zinc-600 underline hover:text-zinc-900"
              >
                {copied === "subject" ? "Copied" : "Copy"}
              </button>
            </div>
            <p className="text-sm text-zinc-900">{draft.draft.subject}</p>
          </div>
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                Body
              </span>
              <button
                type="button"
                onClick={() => copy(draft.draft.body, "body")}
                className="text-xs text-zinc-600 underline hover:text-zinc-900"
              >
                {copied === "body" ? "Copied" : "Copy"}
              </button>
            </div>
            <pre className="whitespace-pre-wrap font-sans text-sm text-zinc-800">
              {draft.draft.body}
            </pre>
          </div>
          <div className="flex flex-wrap items-center gap-3 border-t border-zinc-200 pt-3">
            <button
              type="button"
              onClick={openGmail}
              className="inline-flex items-center gap-2 rounded-md bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-zinc-800"
            >
              <GmailIcon className="h-4 w-4" />
              Open in Gmail
            </button>
            <a
              href={`${BACKEND_URL}/resumes/latest/pdf`}
              target="_blank"
              rel="noreferrer"
              className="text-xs text-zinc-700 underline hover:text-zinc-900"
            >
              Download resume
            </a>
            <button
              type="button"
              onClick={() => setDraft({ status: "idle" })}
              className="ml-auto text-xs text-zinc-500 underline hover:text-zinc-800"
            >
              Clear
            </button>
          </div>
          <p className="text-xs text-zinc-500">
            Gmail doesn't support attachments via URL — attach the resume manually after the compose window opens.
          </p>
        </div>
      )}

      {draft.status === "ready" && draft.draft.kind === "linkedin" && (
        <div className="mt-4 flex flex-col gap-3 rounded-md border border-zinc-200 bg-zinc-50 p-3">
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                LinkedIn message ({draft.draft.message.length} chars)
              </span>
              <button
                type="button"
                onClick={() => copy(draft.draft.message, "message")}
                className="text-xs text-zinc-600 underline hover:text-zinc-900"
              >
                {copied === "message" ? "Copied" : "Copy"}
              </button>
            </div>
            <p className="text-sm text-zinc-800">{draft.draft.message}</p>
          </div>

          <div className="flex flex-col gap-2 border-t border-zinc-200 pt-3">
            <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">
              Founder profiles
            </span>
            {draft.draft.founders.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {draft.draft.founders.map((f) => (
                  <a
                    key={f.linkedin_url}
                    href={f.linkedin_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-2 rounded-md border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-800 hover:border-[#0A66C2] hover:text-[#0A66C2]"
                  >
                    <LinkedInIcon className="h-4 w-4" />
                    {f.name}
                  </a>
                ))}
              </div>
            ) : (
              <p className="text-xs text-zinc-500">
                No founder profiles found on the YC page. Try searching{" "}
                <a
                  href={`https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(
                    job.company_name,
                  )}`}
                  target="_blank"
                  rel="noreferrer"
                  className="underline hover:text-zinc-800"
                >
                  {job.company_name} on LinkedIn
                </a>
                .
              </p>
            )}
          </div>

          <div className="flex items-center gap-3 border-t border-zinc-200 pt-3">
            <p className="text-xs text-zinc-500">
              LinkedIn doesn't allow pre-filled messages — copy the draft, open
              a founder's profile, and paste it into a connection request.
            </p>
            <button
              type="button"
              onClick={() => setDraft({ status: "idle" })}
              className="ml-auto text-xs text-zinc-500 underline hover:text-zinc-800"
            >
              Clear
            </button>
          </div>
        </div>
      )}
    </li>
  );
}
