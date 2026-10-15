import { COUNTRIES, locationRegion } from "../lib/location";
import { useEffect, useState } from "react";

import { apiFetch, BACKEND_URL, type Preferences } from "../lib/api";

type Props = {
  initial: Preferences;
  submitLabel: string;
  onSaved: (preferences: Preferences) => void | Promise<void>;
};

export default function MatchFocusForm({ initial, submitLabel, onSaved }: Props) {
  const [roles, setRoles] = useState(initial.target_roles);
  const [newRole, setNewRole] = useState("");
  const [roleOptions, setRoleOptions] = useState(initial.target_roles);
  const [location, setLocation] = useState(initial.locations[0] ?? "");
  const [workMode, setWorkMode] = useState(initial.work_modes[0] ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setRoles(initial.target_roles);
    setRoleOptions(initial.target_roles);
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
          target_roles: [...new Set([...roles, ...newRole.split(",").map(role => role.trim()).filter(Boolean)])],
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
    <form onSubmit={save} className="grid gap-4">
      <fieldset disabled={saving} className="min-w-0">
        <legend className="mb-3 text-sm font-semibold text-slate-800">Suggested target roles</legend>
        <div className="flex flex-wrap gap-2">{roleOptions.map(role => <button key={role} type="button" aria-pressed={roles.includes(role)} onClick={() => setRoles(current => current.includes(role) ? current.filter(item => item !== role) : [...current,role])} className={`max-w-full rounded-full border px-3 py-2 text-left text-sm ${roles.includes(role) ? "border-indigo-600 bg-indigo-50 font-semibold text-indigo-800" : "border-slate-300 text-slate-600"}`}>{roles.includes(role) ? "✓ " : "+ "}{role}</button>)}</div>
        <label className="mt-4 flex max-w-md flex-col gap-2 text-xs font-semibold text-slate-600">Add a role (optional)<input value={newRole} onChange={event => setNewRole(event.target.value)} placeholder="e.g. Platform Engineer" className="min-h-11 rounded-lg border border-slate-300 px-3 text-sm font-normal" /></label>
        <p className="mt-2 text-xs text-slate-500">No roles selected? We’ll use your resume’s suggested roles.</p>
      </fieldset>
      <details className="rounded-lg border border-slate-200 p-4">
        <summary className="cursor-pointer text-sm font-bold text-slate-800">Fine-tune my search (optional)</summary>
        <p className="my-3 text-xs text-slate-600">Where you want to work can differ from where you live. Leave these open for broader matches.</p>
        <div className="grid gap-4 sm:grid-cols-2">
      <label className="flex flex-col gap-1.5 text-xs font-semibold text-[#43536d]">
        Country (optional)
        <select aria-label="Preferred country" value={locationRegion(location) ?? ""} onChange={event => setLocation(COUNTRIES.find(country => country.region === event.target.value)?.name ?? "")} className="min-h-11 rounded-xl border border-[#ccd5e3] bg-white px-3 text-sm font-normal text-[#172b4d]">
          <option value="">No country preference</option>
          {COUNTRIES.map(country => <option key={country.region} value={country.region}>{country.name}</option>)}
        </select>
        <span className="font-normal text-[#64748b]">Currently collecting YC listings in India and the United States.</span>
      </label>
      <label className="flex flex-col gap-1.5 text-xs font-semibold text-[#43536d]">
        Work mode
        <select value={workMode} onChange={(event) => setWorkMode(event.target.value)} className="min-h-11 rounded-xl border border-[#ccd5e3] bg-white px-3 text-sm font-normal text-[#172b4d] focus:border-[#3859cf] focus:outline-none">
          <option value="">Any work mode</option>
          <option value="remote">Remote</option>
          <option value="hybrid">Hybrid</option>
          <option value="on-site">On-site</option>
        </select>
      </label>
        </div>
      </details>
      {error && <p role="alert" className="text-sm text-red-700">{error}</p>}
      <div className="flex flex-wrap items-center gap-3">
        <button type="submit" disabled={saving} className="min-h-11 rounded-xl bg-[#172b4d] px-5 py-2.5 text-sm font-semibold text-white hover:bg-[#274fc5] disabled:opacity-50">
          {saving ? "Saving..." : submitLabel}
        </button>
        <span className="text-xs text-[#64748b]">Saved privately for this browser.</span>
      </div>
    </form>
  );
}
