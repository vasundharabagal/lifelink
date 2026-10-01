import { Link } from 'react-router-dom';
import { Activity, Zap, LogOut, LogIn } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

/**
 * Sticky top application header for LIFELINK.
 * Shows brand mark, DEMO MODE pill (when demo session active), and auth status.
 */
export function Header() {
  const { user, isAuthenticated, logout } = useAuth();

  const isDemoMode =
    user?.email?.includes('@demo.lifelink.invalid') ||
    import.meta.env.VITE_DEMO_MODE === 'true';

  return (
    <header
      id="app-header"
      className="
        sticky top-0 z-40 bg-white/95 backdrop-blur
        border-b border-slate-200 h-14
        flex items-center justify-between px-4
        max-w-full
      "
    >
      {/* Brand */}
      <Link
        to="/"
        className="
          text-red-600 font-extrabold text-lg
          flex items-center gap-1.5
          focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-600 focus-visible:ring-offset-1
          rounded
        "
        aria-label="LIFELINK — go to home"
      >
        <Activity className="w-5 h-5" aria-hidden="true" />
        LIFELINK
      </Link>

      {/* Right side */}
      <div className="flex items-center gap-3">
        {/* DEMO MODE pill */}
        {isDemoMode && (
          <span
            id="demo-mode-pill"
            className="
              bg-amber-100 text-amber-800 text-xs px-2.5 py-1
              rounded-full font-bold flex items-center gap-1.5
            "
            aria-label="Demo mode active"
          >
            <Zap className="w-3 h-3" aria-hidden="true" />
            DEMO
          </span>
        )}

        {/* Auth status */}
        {isAuthenticated && user ? (
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-600 hidden sm:block truncate max-w-[120px]">
              {user.full_name || user.email}
            </span>
            <button
              onClick={logout}
              className="
                flex items-center gap-1 text-xs text-slate-500
                hover:text-slate-900 transition-colors
                min-h-[36px] px-2 rounded
                focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-1
              "
              aria-label="Log out"
            >
              <LogOut className="w-3.5 h-3.5" aria-hidden="true" />
              <span className="hidden sm:block">Logout</span>
            </button>
          </div>
        ) : (
          <Link
            to="/login"
            className="
              flex items-center gap-1 text-xs text-slate-500
              hover:text-slate-900 transition-colors
              min-h-[36px] px-2 rounded
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-1
            "
            aria-label="Log in to LIFELINK"
          >
            <LogIn className="w-3.5 h-3.5" aria-hidden="true" />
            Login
          </Link>
        )}
      </div>
    </header>
  );
}
