import { Link, useLocation } from "react-router-dom";

import { useAuth } from "@/hooks/useAuth";

export function Header() {
  const { user, signOut, loading } = useAuth();
  const { pathname } = useLocation();

  return (
    <header className="border-b border-slate-200 bg-white/80 backdrop-blur-sm">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary-600">
              <svg
                className="h-5 w-5 text-white"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={2.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 4.5v15m7.5-7.5h-15"
                />
              </svg>
            </div>
            <span className="text-lg font-bold tracking-tight text-slate-900">
              emerg<span className="text-primary-600">AI</span>
            </span>
          </Link>

          <nav className="hidden items-center gap-1 sm:flex">
            <NavLink to="/" current={pathname === "/"}>
              Kiosk
            </NavLink>
            <NavLink to="/dashboard" current={pathname === "/dashboard"}>
              Dashboard
            </NavLink>
          </nav>
        </div>

        <div className="flex items-center gap-4">
          <StatusDot />
          {!loading && user && (
            <button
              onClick={() => void signOut()}
              className="text-sm font-medium text-slate-500 transition-colors hover:text-slate-700"
            >
              Sign out
            </button>
          )}
        </div>
      </div>
    </header>
  );
}

function NavLink({
  to,
  current,
  children,
}: {
  to: string;
  current: boolean;
  children: React.ReactNode;
}) {
  return (
    <Link
      to={to}
      className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
        current
          ? "bg-primary-50 text-primary-700"
          : "text-slate-500 hover:bg-slate-100 hover:text-slate-700"
      }`}
    >
      {children}
    </Link>
  );
}

function StatusDot() {
  return (
    <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
      <span className="relative flex h-2.5 w-2.5">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent-400 opacity-75" />
        <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-accent-500" />
      </span>
      System Online
    </div>
  );
}
