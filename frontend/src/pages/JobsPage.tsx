import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { BACKEND_URL, type Preferences } from "../lib/api";

export default function JobsPage() {
  const [prefs, setPrefs] = useState<Preferences | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    fetch(`${BACKEND_URL}/preferences`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!cancelled) setPrefs(data);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold tracking-tight text-zinc-900">
          Jobs
        </h1>
        <p className="text-zinc-600">
          Matched openings will appear here once scraping is wired up.
        </p>
      </header>

      <section className="rounded-lg border border-dashed border-zinc-300 bg-white p-10 text-center">
        {loading ? (
          <p className="text-sm text-zinc-500">Loading…</p>
        ) : !prefs?.has_saved ? (
          <>
            <p className="text-sm font-medium text-zinc-700">
              Save your preferences first.
            </p>
            <p className="mt-2 text-xs text-zinc-500">
              Head to{" "}
              <Link to="/" className="text-zinc-900 underline hover:text-zinc-700">
                Setup
              </Link>{" "}
              and save your preferences — matched jobs will populate here once
              scraping is wired up.
            </p>
          </>
        ) : (
          <>
            <p className="text-sm font-medium text-zinc-700">No jobs yet.</p>
            <p className="mt-2 text-xs text-zinc-500">
              Coming next: YC scraping, resume↔job matching, per-job apply with
              drafted email and LinkedIn message.
            </p>
          </>
        )}
      </section>
    </div>
  );
}
