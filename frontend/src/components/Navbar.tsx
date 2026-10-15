import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "My profile", end: true },
  { to: "/jobs", label: "Discover jobs" },
];

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-10 border-b border-[#dce2ec] bg-[#ffffff]/95 backdrop-blur-xl">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-3 px-5 py-4 sm:px-8">
        <NavLink to="/" className="flex items-center gap-2 text-lg font-bold tracking-[-0.05em] text-[#172b4d]">
          <span aria-hidden="true" className="grid h-8 w-8 place-items-center rounded-xl bg-[#172b4d] text-lg text-[#ffffff]">↗</span>
          <span>hireme<span className="text-[#3859cf]">now</span></span>
        </NavLink>
        <div className="flex items-center gap-1 rounded-lg border border-[#dce2ec] bg-white p-1 shadow-sm">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) =>
                `rounded-lg px-3 py-1.5 text-xs font-semibold transition sm:px-4 sm:text-sm ${
                  isActive
                    ? "bg-[#172b4d] text-white shadow-sm"
                    : "text-[#596980] hover:bg-[#eef2ff]"
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </div>
      </div>
    </nav>
  );
}
