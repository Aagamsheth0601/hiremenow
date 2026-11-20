import { NavLink } from "react-router-dom";

const links = [
  { to: "/", label: "My profile", end: true },
  { to: "/jobs", label: "Discover jobs" },
];

export default function Navbar() {
  return (
    <nav className="workspace-nav sticky top-0 z-20">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-3 px-5 py-4 sm:px-8">
        <NavLink to="/" className="wordmark">
          <span aria-hidden="true" className="brand-mark">↗</span>
          <span>hireme<span className="brand-accent">now</span></span>
        </NavLink>
        <div className="workspace-tabs">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.end}
              className="workspace-tab"
            >
              {l.label}
            </NavLink>
          ))}
        </div>
      </div>
    </nav>
  );
}
