import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "My profile", end: true },
  { to: "/jobs", label: "Discover jobs" },
];

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-10 border-b border-[#dce5dc] bg-[#f7f8f4]/95 backdrop-blur-xl">
      <div className="mx-auto flex w-full max-w-6xl items-center justify-between gap-3 px-5 py-4 sm:px-8">
        <NavLink to="/" className="flex items-center gap-2 text-lg font-bold tracking-[-0.05em] text-[#18342f]">
          <span aria-hidden="true" className="grid h-8 w-8 place-items-center rounded-xl bg-[#173e35] text-lg text-[#d0e8c8]">✳</span>
          <span>hireme<span className="text-[#59966e]">now</span></span>
        </NavLink>
        <div className="flex items-center gap-1 rounded-full border border-[#dce5dc] bg-white p-1 shadow-sm">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className={({ isActive }) =>
                `rounded-full px-3 py-1.5 text-xs font-semibold transition sm:px-4 sm:text-sm ${
                  isActive
                    ? "bg-[#173e35] text-white shadow-sm"
                    : "text-[#567268] hover:bg-[#edf4ed]"
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
