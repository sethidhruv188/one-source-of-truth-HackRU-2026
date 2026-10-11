import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

const NAV = [
  { key: "overview", path: "/",         label: "Overview",     always: true },
  { key: "ask",      path: "/ask",      label: "Ask" },
  { key: "graph",    path: "/graph",    label: "Graph" },
  { key: "catalog",  path: "/catalog",  label: "Catalog" },
  { key: "review",   path: "/review",   label: "Review queue" },
  { key: "health",   path: "/health",   label: "Data health" },
  { key: "about",    path: "/about",    label: "How it works" },
];

function initials(name = "") {
  return name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
}

export default function Shell({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const allowed = new Set(user.views || []);

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="w-60 shrink-0 bg-ink-800 border-r border-line flex flex-col">
        <div className="px-5 py-5 border-b border-line">
          <div className="flex items-center gap-2.5">
            <div className="h-7 w-7 rounded bg-accent/15 border border-accent/30 grid place-items-center">
              <div className="h-2 w-2 rounded-sm bg-accent" />
            </div>
            <div className="leading-tight">
              <div className="text-[13px] font-semibold tracking-tight">One Source of Truth</div>
              <div className="text-[10px] text-mist-700">Clinical trial data</div>
            </div>
          </div>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
          {NAV.filter((n) => n.always || allowed.has(n.key)).map((n) => (
            <NavLink key={n.key} to={n.path} end={n.path === "/"}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-[13px] transition-colors ${
                  isActive
                    ? "bg-accent-soft text-accent font-medium"
                    : "text-mist-300 hover:bg-ink-600 hover:text-mist-100"
                }`}>
              {n.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-line p-3">
          <div className="flex items-center gap-3 px-2 py-2">
            <div className="h-8 w-8 rounded-full bg-accent/15 border border-accent/30
                            grid place-items-center text-[11px] font-semibold text-accent shrink-0">
              {initials(user.name)}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[13px] font-medium truncate">{user.name}</div>
              <div className="text-[11px] text-mist-500 truncate">{user.role}</div>
            </div>
          </div>
          <button onClick={() => { logout(); navigate("/"); }}
                  className="w-full mt-1 px-3 py-1.5 rounded-md text-[12px] text-mist-500
                             hover:bg-ink-600 hover:text-mist-100 transition-colors text-left">
            Sign out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-[1500px] mx-auto px-8 py-7">{children}</div>
      </main>
    </div>
  );
}
