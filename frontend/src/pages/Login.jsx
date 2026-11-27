import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { formatApiError } from "../api/client";
import ErrorMessage from "../components/ErrorMessage";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const registeredMessage = location.state?.message || "";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      const profile = await login({ email, password });
      if (profile.role === "DONOR") {
        navigate("/donor", { replace: true });
      } else {
        navigate("/profile", { replace: true });
      }
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto mt-8 max-w-md rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
      <h1 className="text-2xl font-bold text-stone-900">Welcome back</h1>
      <p className="mt-1 text-sm text-stone-600">
        Sign in to your FoodShare account.
      </p>

      {registeredMessage && (
        <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {registeredMessage}
        </div>
      )}

      <div className="mt-4">
        <ErrorMessage message={error} onDismiss={() => setError("")} />
      </div>

      <form onSubmit={handleSubmit} className="mt-4 space-y-4">
        <div>
          <label className="block text-sm font-medium text-stone-700">Email</label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-stone-700">Password</label>
          <input
            type="password"
            required
            maxLength={72}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? "Signing in..." : "Sign In"}
        </button>
      </form>

      <p className="mt-5 text-center text-sm text-stone-600">
        Don&apos;t have an account?{" "}
        <Link to="/register" className="font-semibold text-emerald-700 hover:underline">
          Register here
        </Link>
      </p>
    </div>
  );
}
