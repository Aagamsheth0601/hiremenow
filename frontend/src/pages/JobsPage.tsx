import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";

import {
  apiFetch,
  BACKEND_URL,
  type ApplicationStatus,
  type EmailDraft,
  type Job,
  type LinkedInDraft,
  type Preferences,
  type ScrapeResult,
  type StatusCounts,
  type StatusFilter,
} from "../lib/api";

const STATUS_OPTIONS: { value: ApplicationStatus; label: string; color: string }[] = [
  { value: "reached_out", label: "Reached out", color: "bg-amber-100 text-amber-800" },
  { value: "applied", label: "Applied", color: "bg-blue-100 text-blue-800" },
  { value: "replied", label: "Replied", color: "bg-purple-100 text-purple-800" },
  { value: "rejected", label: "Rejected", color: "bg-zinc-200 text-zinc-700" },
];

const STATUS_FILTERS: { value: StatusFilter; label: string }[] = [
  { value: "active", label: "Active" },
  { value: "starred", label: "Starred" },
  { value: "reached_out", label: "Reached out" },
  { value: "applied", label: "Applied" },
  { value: "replied", label: "Replied" },
  { value: "rejected", label: "Rejected" },
  { value: "all", label: "All" },
];

function StarIcon({
  filled,
  className = "",
}: {
  filled: boolean;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={className}
      fill={filled ? "#F59E0B" : "none"}
      stroke={filled ? "#F59E0B" : "currentColor"}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  );
}

function statusMeta(status: ApplicationStatus | null) {
  if (!status) return null;
  return STATUS_OPTIONS.find((o) => o.value === status) ?? null;
}

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
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("active");
  const [sortDir, setSortDir] = useState<"desc" | "asc">("desc");
  const [page, setPage] = useState(0);
  const [counts, setCounts] = useState<StatusCounts | null>(null);
  const enrichRequestedRef = useRef<Set<number>>(new Set());

  const loadCounts = useCallback(async (regionParam: "india" | "us") => {
    try {
      const res = await apiFetch(
        `${BACKEND_URL}/jobs/status-counts?region=${regionParam}`,
      );
      if (!res.ok) return;
      setCounts((await res.json()) as StatusCounts);
    } catch (err) {
      console.error("failed to load status counts", err);
    }
  }, []);

  const loadJobs = useCallback(
    async (regionParam: "india" | "us", statusParam: StatusFilter) => {
      setJobsLoading(true);
      try {
        const res = await apiFetch(
          `${BACKEND_URL}/jobs?limit=200&region=${regionParam}&application_status=${statusParam}`,
        );
        if (!res.ok) throw new Error(`status ${res.status}`);
        const data: Job[] = await res.json();
        setJobs(data);
      } catch (err) {
        console.error("failed to load jobs", err);
      } finally {
        setJobsLoading(false);
      }
    },
    [],
  );

  const handleStatusChange = useCallback(
    (jobId: number, newStatus: ApplicationStatus | null) => {
      const matchesFilter =
        statusFilter === "all" ||
        statusFilter === "starred" ||
        (statusFilter === "active" && newStatus === null) ||
        statusFilter === newStatus;

      setJobs((prev) =>
        matchesFilter
          ? prev.map((j) =>
              j.id === jobId
                ? {
                    ...j,
                    application_status: newStatus,
                    status_updated_at: newStatus ? new Date().toISOString() : null,
                  }
                : j,
            )
          : prev.filter((j) => j.id !== jobId),
      );
      loadCounts(region);
    },
    [loadCounts, region, statusFilter],
  );

  const handleStarChange = useCallback(
    (jobId: number, isStarred: boolean) => {
      setJobs((prev) =>
        statusFilter === "starred" && !isStarred
          ? prev.filter((j) => j.id !== jobId)
          : prev.map((j) => (j.id === jobId ? { ...j, is_starred: isStarred } : j)),
      );
      loadCounts(region);
    },
    [loadCounts, region, statusFilter],
  );

  useEffect(() => {
    let cancelled = false;
    apiFetch(`${BACKEND_URL}/preferences`)
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
    setPage(0);
    loadJobs(region, statusFilter);
  }, [loadJobs, region, statusFilter]);

  useEffect(() => {
    loadCounts(region);
  }, [loadCounts, region]);

  useEffect(() => {
    enrichRequestedRef.current = new Set();
  }, [region, statusFilter]);

  useEffect(() => {
    if (jobs.length === 0) return;
    const targets = jobs
      .filter(
        (j) =>
          j.founders.length === 0 &&
          j.contact_emails.length === 0 &&
          !enrichRequestedRef.current.has(j.id),
      )
      .slice(0, 20)
      .map((j) => j.id);
    if (targets.length === 0) return;
    targets.forEach((id) => enrichRequestedRef.current.add(id));

    let cancelled = false;
    apiFetch(`${BACKEND_URL}/jobs/enrich-batch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_ids: targets, force: false }),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data: Record<string, { founders: Job["founders"]; contact_emails: string[] }> | null) => {
        if (cancelled || !data) return;
        setJobs((prev) =>
          prev.map((j) => {
            const enriched = data[String(j.id)];
            return enriched
              ? {
                  ...j,
                  founders: enriched.founders,
                  contact_emails: enriched.contact_emails,
                }
              : j;
          }),
        );
      })
      .catch((err) => console.error("batch enrich failed", err));

    return () => {
      cancelled = true;
    };
  }, [jobs]);

  const JOBS_PER_PAGE = 30;

  const sortedJobs = useMemo(() => {
    return [...jobs].sort((a, b) => {
      const sa = a.match_score ?? 0;
      const sb = b.match_score ?? 0;
      return sortDir === "desc" ? sb - sa : sa - sb;
    });
  }, [jobs, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sortedJobs.length / JOBS_PER_PAGE));
  const pagedJobs = sortedJobs.slice(page * JOBS_PER_PAGE, (page + 1) * JOBS_PER_PAGE);

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
      const res = await apiFetch(
        `${BACKEND_URL}/jobs/scrape?company_limit=25&job_limit_per_company=5&region=${region}`,
        { method: "POST" },
      );
      if (!res.ok) throw new Error(`status ${res.status}`);
      const data: ScrapeResult = await res.json();
      const regionLabel = region === "india" ? "India" : "US";
      setScrapeMsg(
        `Scraped ${data.companies_visited} ${regionLabel} companies — ${data.jobs_inserted} new, ${data.jobs_updated} updated (total ${data.total_jobs_in_db}).`,
      );
      await loadJobs(region, statusFilter);
      loadCounts(region);
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
              Sorted by match score (out of 10, {sortDir === "desc" ? "highest first" : "lowest first"}) — overlap of job title and
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

      <div className="flex flex-wrap items-center gap-2">
        {STATUS_FILTERS.map((f) => {
          const active = statusFilter === f.value;
          const count = counts?.[f.value];
          return (
            <button
              key={f.value}
              type="button"
              onClick={() => setStatusFilter(f.value)}
              className={`rounded-full border px-3 py-1 text-xs transition ${
                active
                  ? "border-zinc-900 bg-zinc-900 text-white"
                  : "border-zinc-300 bg-white text-zinc-700 hover:border-zinc-500"
              }`}
            >
              {f.label}
              {count !== undefined && (
                <span
                  className={`ml-1.5 ${active ? "text-zinc-300" : "text-zinc-400"}`}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}

        <span className="mx-1 h-4 w-px bg-zinc-300" />

        <button
          type="button"
          onClick={() => setSortDir((d) => (d === "desc" ? "asc" : "desc"))}
          className="inline-flex items-center gap-1 rounded-full border border-zinc-300 bg-white px-3 py-1 text-xs text-zinc-700 transition hover:border-zinc-500"
        >
          Score {sortDir === "desc" ? "↓" : "↑"}
        </button>
      </div>

      {jobsLoading ? (
        <div className="rounded-lg border border-dashed border-zinc-300 bg-white p-10 text-center text-sm text-zinc-500">
          Loading jobs…
        </div>
      ) : pagedJobs.length === 0 ? (
        <div className="rounded-lg border border-dashed border-zinc-300 bg-white p-10 text-center">
          <p className="text-sm font-medium text-zinc-700">No jobs yet.</p>
          <p className="mt-2 text-xs text-zinc-500">
            Hit “Scrape now” to pull the latest YC openings.
          </p>
        </div>
      ) : (
        <>
          <ul className="flex flex-col gap-3">
            {pagedJobs.map((job) => (
              <JobCard
                key={job.id}
                job={job}
                onStatusChange={handleStatusChange}
                onStarChange={handleStarChange}
              />
            ))}
          </ul>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-3 pt-2">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm text-zinc-700 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-sm text-zinc-600">
                Page {page + 1} of {totalPages}
              </span>
              <button
                type="button"
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-sm text-zinc-700 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                Next
              </button>
            </div>
          )}
        </>
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

function JobCard({
  job: initialJob,
  onStatusChange,
  onStarChange,
}: {
  job: Job;
  onStatusChange: (jobId: number, newStatus: ApplicationStatus | null) => void;
  onStarChange: (jobId: number, isStarred: boolean) => void;
}) {
  const [job, setJob] = useState(initialJob);
  const [draft, setDraft] = useState<DraftState>({ status: "idle" });
  const [copied, setCopied] = useState<"subject" | "body" | "message" | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [enriching, setEnriching] = useState(false);
  const [updatingStatus, setUpdatingStatus] = useState(false);
  const [updatingStar, setUpdatingStar] = useState(false);
  const [showDescription, setShowDescription] = useState(false);

  const toggleStar = async () => {
    const next = !job.is_starred;
    setUpdatingStar(true);
    setJob({ ...job, is_starred: next });
    try {
      const res = await apiFetch(`${BACKEND_URL}/jobs/${job.id}/star`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_starred: next }),
      });
      if (!res.ok) throw new Error(`status ${res.status}`);
      onStarChange(job.id, next);
    } catch (err) {
      console.error("star toggle failed", err);
      setJob({ ...job, is_starred: !next });
    } finally {
      setUpdatingStar(false);
    }
  };

  const setStatus = async (newStatus: ApplicationStatus | null) => {
    setUpdatingStatus(true);
    try {
      const res = await apiFetch(`${BACKEND_URL}/jobs/${job.id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus }),
      });
      if (!res.ok) throw new Error(`status ${res.status}`);
      const data: {
        application_status: ApplicationStatus | null;
        status_updated_at: string | null;
      } = await res.json();
      setJob({
        ...job,
        application_status: data.application_status,
        status_updated_at: data.status_updated_at,
      });
      onStatusChange(job.id, data.application_status);
    } catch (err) {
      console.error("status update failed", err);
    } finally {
      setUpdatingStatus(false);
    }
  };

  const meta = statusMeta(job.application_status);

  const enrich = async () => {
    setEnriching(true);
    try {
      const res = await apiFetch(`${BACKEND_URL}/jobs/${job.id}/enrich`, {
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

  const generate = async (kind: DraftKind, options: { force?: boolean } = {}) => {
    setDraft({ status: "loading", kind });
    setCopied(null);
    try {
      if (!options.force && job.draft_kinds.includes(kind)) {
        const cached = await apiFetch(
          `${BACKEND_URL}/jobs/${job.id}/draft?kind=${kind}`,
        );
        if (cached.ok) {
          const data = (await cached.json()) as EmailDraft | LinkedInDraft;
          setDraft({ status: "ready", kind, draft: data });
          return;
        }
      }

      const res = await apiFetch(
        `${BACKEND_URL}/jobs/${job.id}/draft?kind=${kind}`,
        { method: "POST" },
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail ?? `Draft failed (${res.status})`);
      }
      const data = (await res.json()) as EmailDraft | LinkedInDraft;
      setDraft({ status: "ready", kind, draft: data });
      if (!job.draft_kinds.includes(kind)) {
        setJob({ ...job, draft_kinds: [...job.draft_kinds, kind] });
      }
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

  const downloadResume = async () => {
    setDownloadError(null);
    try {
      const response = await apiFetch(`${BACKEND_URL}/resumes/latest/pdf`);
      if (!response.ok) throw new Error("Could not download your resume.");
      const objectUrl = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = "resume.pdf";
      link.click();
      setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : "Download failed.");
    }
  };

  const emailDraft = draft.status === "ready" && draft.draft.kind === "email" ? draft.draft : null;
  const linkedInDraft = draft.status === "ready" && draft.draft.kind === "linkedin" ? draft.draft : null;

  return (
    <li className="group rounded-lg border border-zinc-200 bg-white p-4 shadow-sm transition hover:border-zinc-300 hover:shadow-md">
      <div className="flex items-start gap-4">
        <div className="flex flex-1 flex-col gap-1">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={toggleStar}
              disabled={updatingStar}
              title={job.is_starred ? "Unstar" : "Star this job"}
              className="rounded-full p-1 transition hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <StarIcon filled={job.is_starred} className="h-4 w-4" />
            </button>
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

          {job.match_details && (
            <details className="mt-3 rounded-lg border border-emerald-100 bg-emerald-50/60 px-3 py-2 text-sm">
              <summary className="cursor-pointer font-medium text-emerald-950">
                Why this match
                {job.match_details.matched_skills.length > 0 && (
                  <span className="ml-2 font-normal text-emerald-800">
                    {job.match_details.matched_skills.slice(0, 3).join(" · ")}
                  </span>
                )}
              </summary>
              <div className="mt-2 space-y-1 text-xs leading-relaxed text-slate-700">
                {job.match_details.matched_target_roles.length > 0 && (
                  <p>Role match: {job.match_details.matched_target_roles.join(", ")}</p>
                )}
                <p>Skills in both your resume and this job post: {job.match_details.matched_skills.join(", ") || "none identified"}.</p>
                {job.match_details.missing_skills.length > 0 && (
                  <p>Job post also mentions: {job.match_details.missing_skills.join(", ")}. Check whether these appear elsewhere in your resume.</p>
                )}
                <p className="text-slate-500">This score uses extracted text and is a guide, not an employer assessment.</p>
              </div>
            </details>
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

          {job.description && (
            <div className="mt-3">
              <button
                type="button"
                onClick={() => setShowDescription((v) => !v)}
                className="text-xs text-zinc-600 underline hover:text-zinc-900"
              >
                {showDescription ? "Hide description" : "Show description"}
              </button>
              {showDescription && (
                <div className="mt-2 max-h-72 overflow-y-auto rounded-md border border-zinc-200 bg-zinc-50 p-3">
                  <pre className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-zinc-800">
                    {job.description}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex flex-col items-end gap-2">
          <span className="text-xs text-zinc-400">
            Job posted {timeAgo(job.scraped_at)}
          </span>
          {meta && (
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${meta.color}`}
            >
              {meta.label}
            </span>
          )}
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => generate("email")}
              disabled={draft.status === "loading"}
              title={
                job.draft_kinds.includes("email")
                  ? "Open saved Gmail draft"
                  : "Draft & open in Gmail"
              }
              className="relative rounded-md border border-zinc-200 p-1.5 transition hover:border-zinc-400 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {draft.status === "loading" && draft.kind === "email" ? (
                <span className="block h-5 w-5 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-700" />
              ) : (
                <GmailIcon className="h-5 w-5" />
              )}
              {job.draft_kinds.includes("email") && (
                <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-emerald-500 ring-2 ring-white" />
              )}
            </button>
            <button
              type="button"
              onClick={() => generate("linkedin")}
              disabled={draft.status === "loading"}
              title={
                job.draft_kinds.includes("linkedin")
                  ? "Open saved LinkedIn draft"
                  : "Draft & open LinkedIn"
              }
              className="relative rounded-md border border-zinc-200 p-1.5 transition hover:border-zinc-400 hover:bg-zinc-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {draft.status === "loading" && draft.kind === "linkedin" ? (
                <span className="block h-5 w-5 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-700" />
              ) : (
                <LinkedInIcon className="h-5 w-5" />
              )}
              {job.draft_kinds.includes("linkedin") && (
                <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-emerald-500 ring-2 ring-white" />
              )}
            </button>
          </div>
          <select
            value={job.application_status ?? ""}
            onChange={(e) =>
              setStatus(e.target.value === "" ? null : (e.target.value as ApplicationStatus))
            }
            disabled={updatingStatus}
            className="w-full rounded-md border border-zinc-300 bg-white px-2 py-1 text-xs text-zinc-700 hover:border-zinc-500 disabled:cursor-not-allowed disabled:opacity-50"
            title="Mark application status"
          >
            <option value="">Mark status…</option>
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {draft.status === "error" && (
        <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">
          {draft.message}
        </p>
      )}

      {emailDraft && (
        <div className="mt-4 flex flex-col gap-3 rounded-md border border-zinc-200 bg-zinc-50 p-3">
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">
              Recipients
            </span>
            {emailDraft.recipients.length > 0 ? (
              <p className="text-sm text-zinc-900">
                {emailDraft.recipients.join(", ")}
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
                onClick={() => copy(emailDraft.subject, "subject")}
                className="text-xs text-zinc-600 underline hover:text-zinc-900"
              >
                {copied === "subject" ? "Copied" : "Copy"}
              </button>
            </div>
            <p className="text-sm text-zinc-900">{emailDraft.subject}</p>
          </div>
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                Body
              </span>
              <button
                type="button"
                onClick={() => copy(emailDraft.body, "body")}
                className="text-xs text-zinc-600 underline hover:text-zinc-900"
              >
                {copied === "body" ? "Copied" : "Copy"}
              </button>
            </div>
            <pre className="whitespace-pre-wrap font-sans text-sm text-zinc-800">
              {emailDraft.body}
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
            <button
              type="button"
              onClick={downloadResume}
              className="text-xs text-zinc-700 underline hover:text-zinc-900"
            >
              Download resume
            </button>
            <button
              type="button"
              onClick={() => generate("email", { force: true })}
              className="ml-auto text-xs text-zinc-500 underline hover:text-zinc-800"
            >
              Regenerate
            </button>
            <button
              type="button"
              onClick={() => setDraft({ status: "idle" })}
              className="text-xs text-zinc-500 underline hover:text-zinc-800"
            >
              Clear
            </button>
          </div>
          <p className="text-xs text-zinc-500">
            Gmail doesn't support attachments via URL — attach the resume manually after the compose window opens.
          </p>
          {downloadError && <p role="alert" className="text-xs text-red-700">{downloadError}</p>}
        </div>
      )}

      {linkedInDraft && (
        <div className="mt-4 flex flex-col gap-3 rounded-md border border-zinc-200 bg-zinc-50 p-3">
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">
                LinkedIn message ({linkedInDraft.message.length} chars)
              </span>
              <button
                type="button"
                onClick={() => copy(linkedInDraft.message, "message")}
                className="text-xs text-zinc-600 underline hover:text-zinc-900"
              >
                {copied === "message" ? "Copied" : "Copy"}
              </button>
            </div>
            <p className="text-sm text-zinc-800">{linkedInDraft.message}</p>
          </div>

          <div className="flex flex-col gap-2 border-t border-zinc-200 pt-3">
            <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">
              Founder profiles
            </span>
            {linkedInDraft.founders.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {linkedInDraft.founders.map((f) => (
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
              onClick={() => generate("linkedin", { force: true })}
              className="ml-auto text-xs text-zinc-500 underline hover:text-zinc-800"
            >
              Regenerate
            </button>
            <button
              type="button"
              onClick={() => setDraft({ status: "idle" })}
              className="text-xs text-zinc-500 underline hover:text-zinc-800"
            >
              Clear
            </button>
          </div>
        </div>
      )}
    </li>
  );
}
