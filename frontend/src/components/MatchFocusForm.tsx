import { useEffect, useState } from "react";

import { apiFetch, BACKEND_URL, type Preferences } from "../lib/api";

type Props = {
  initial: Preferences;
  submitLabel: string;
  onSaved: (preferences: Preferences) => void | Promise<void>;
};

export default function MatchFocusForm({ initial, submitLabel, onSaved }: Props) {
  const [roles, setRoles] = useState(initial.target_roles.join(", "));
  const [location, setLocation] = useState(initial.locations[0] ?? "");
  const [workMode, setWorkMode] = useState(initial.work_modes[0] ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setRoles(initial.target_roles.join(", "));
    setLocation(initial.locations[0] ?? "");
    setWorkMode(initial.work_modes[0] ?? "");
  }, [initial]);

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const response = await apiFetch(`${BACKEND_URL}/preferences`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_roles: roles.split(",").map((role) => role.trim()).filter(Boolean),
          locations: location.trim() ? [location.trim()] : [],
          work_modes: workMode ? [workMode] : [],
          seniority: initial.seniority,
          company_sizes: initial.company_sizes,
          needs_visa_sponsorship: initial.needs_visa_sponsorship,
        }),
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail ?? `Could not save your match focus (${response.status}).`);
      }
      await onSaved(await response.json() as Preferences);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not save your match focus.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={save} className="grid gap-4 md:grid-cols-3">
      <label className="flex flex-col gap-1.5 text-xs font-semibold text-[#365f4b]">
        Target roles
        <input value={roles} onChange={(event) => setRoles(event.target.value)} placeholder="Backend Engineer, Data Analyst" className="min-h-11 rounded-xl border border-[#ccdccc] bg-white px-3 text-sm font-normal text-[#173e35] focus:border-[#59966e] focus:outline-none" />
        <span className="font-normal text-[#7b9485]">Separate multiple roles with commas.</span>
      </label>
      <label className="flex flex-col gap-1.5 text-xs font-semibold text-[#365f4b]">
        Preferred city or country
        <input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Mumbai, India" className="min-h-11 rounded-xl border border-[#ccdccc] bg-white px-3 text-sm font-normal text-[#173e35] focus:border-[#59966e] focus:outline-none" />
        <span className="font-normal text-[#7b9485]">Leave blank to see any location.</span>
      </label>
      <label className="flex flex-col gap-1.5 text-xs font-semibold text-[#365f4b]">
        Work mode
        <select value={workMode} onChange={(event) => setWorkMode(event.target.value)} className="min-h-11 rounded-xl border border-[#ccdccc] bg-white px-3 text-sm font-normal text-[#173e35] focus:border-[#59966e] focus:outline-none">
          <option value="">Any work mode</option>
          <option value="remote">Remote</option>
          <option value="hybrid">Hybrid</option>
          <option value="on-site">On-site</option>
        </select>
      </label>
      {error && <p role="alert" className="text-sm text-red-700 md:col-span-3">{error}</p>}
      <div className="flex flex-wrap items-center gap-3 md:col-span-3">
        <button type="submit" disabled={saving} className="min-h-11 rounded-xl bg-[#173e35] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#285846] disabled:opacity-50">
          {saving ? "Saving..." : submitLabel}
        </button>
        <span className="text-xs text-[#7b9485]">Saved privately for this browser.</span>
      </div>
    </form>
  );
}
