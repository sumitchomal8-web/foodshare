import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = () => {
    logout();
    setMenuOpen(false);
    navigate("/login");
  };

  const linkClass = ({ isActive }) =>
    `rounded-lg px-3 py-1.5 text-sm font-medium transition ${
      isActive
        ? "bg-emerald-50 text-emerald-700"
        : "text-stone-600 hover:bg-stone-100 hover:text-stone-900"
    }`;

  return (
    <header className="sticky top-0 z-20 border-b border-stone-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-600 text-sm font-bold text-white">
            FS
          </span>
          <span className="text-lg font-bold tracking-tight text-stone-900">
            FoodShare
          </span>
        </Link>

        <button
          type="button"
          onClick={() => setMenuOpen((prev) => !prev)}
          className="rounded-lg border border-stone-200 px-2.5 py-1.5 text-sm text-stone-700 md:hidden"
        >
          Menu
        </button>

        <nav className="hidden items-center gap-2 md:flex">
          {!isAuthenticated ? (
            <>
              <NavLink to="/login" className={linkClass}>
                Login
              </NavLink>
              <NavLink
                to="/register"
                className="rounded-lg bg-emerald-600 px-3.5 py-1.5 text-sm font-medium text-white hover:bg-emerald-700"
              >
                Register
              </NavLink>
            </>
          ) : (
            <>
              {user.role === "DONOR" && (
                <NavLink to="/donor" className={linkClass}>
                  My Donations
                </NavLink>
              )}
              <NavLink to="/profile" className={linkClass}>
                Profile
              </NavLink>
              <span className="ml-2 rounded-full bg-stone-100 px-2.5 py-0.5 text-xs font-semibold text-stone-700">
                {user.role}
              </span>
              <button
                type="button"
                onClick={handleLogout}
                className="ml-2 rounded-lg border border-stone-300 px-3 py-1.5 text-sm font-medium text-stone-700 hover:bg-stone-100"
              >
                Logout
              </button>
            </>
          )}
        </nav>
      </div>

      {menuOpen && (
        <div className="border-t border-stone-200 bg-white px-4 py-3 md:hidden">
          <div className="flex flex-col gap-2">
            {!isAuthenticated ? (
              <>
                <NavLink to="/login" className={linkClass} onClick={() => setMenuOpen(false)}>
                  Login
                </NavLink>
                <NavLink to="/register" className={linkClass} onClick={() => setMenuOpen(false)}>
                  Register
                </NavLink>
              </>
            ) : (
              <>
                {user.role === "DONOR" && (
                  <NavLink to="/donor" className={linkClass} onClick={() => setMenuOpen(false)}>
                    My Donations
                  </NavLink>
                )}
                <NavLink to="/profile" className={linkClass} onClick={() => setMenuOpen(false)}>
                  Profile
                </NavLink>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="rounded-lg border border-stone-300 px-3 py-1.5 text-left text-sm font-medium text-stone-700"
                >
                  Logout ({user.role})
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
