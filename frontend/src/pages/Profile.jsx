import { useEffect, useState } from "react";
import { formatApiError } from "../api/client";
import { updateMyProfile } from "../api/users";
import ErrorMessage from "../components/ErrorMessage";
import Loading from "../components/Loading";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../context/AuthContext";

export default function Profile() {
  const { user, loading, refreshUser } = useAuth();
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState({
    street: "",
    city: "",
    state: "",
    pincode: "",
  });

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user) {
      setName(user.name || "");
      setPhone(user.phone || "");
      setAddress(
        user.address || { street: "", city: "", state: "", pincode: "" }
      );
    }
  }, [user]);

  if (loading || !user) {
    return <Loading message="Loading profile..." />;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setSaving(true);

    try {
      await updateMyProfile({ name, phone, address });
      await refreshUser();
      setSuccess("Profile updated successfully.");
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  const inputClass =
    "mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500";

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-stone-900">{user.name}</h1>
            <p className="text-sm text-stone-600">{user.email}</p>
          </div>
          <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-800">
            {user.role}
          </span>
        </div>

        {user.ngo_profile && (
          <div className="mt-4 rounded-lg border border-stone-200 bg-stone-50 p-4 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-semibold text-stone-900">
                {user.ngo_profile.organization_name} ({user.ngo_profile.org_type})
              </span>
              <StatusBadge status={user.ngo_profile.verification_status} />
            </div>
            {user.ngo_profile.registration_number && (
              <p className="mt-1 text-stone-600">
                Registration #: {user.ngo_profile.registration_number}
              </p>
            )}
          </div>
        )}
      </div>

      <div className="rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-stone-900">Edit Profile</h2>

        <div className="mt-4">
          <ErrorMessage message={error} onDismiss={() => setError("")} />
          {success && (
            <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
              {success}
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-sm font-medium text-stone-700">Full Name</label>
              <input
                type="text"
                required
                minLength={1}
                value={name}
                onChange={(e) => setName(e.target.value)}
                className={inputClass}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-stone-700">Phone</label>
              <input
                type="text"
                required
                minLength={1}
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className={inputClass}
              />
            </div>

            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-stone-700">Street</label>
              <input
                type="text"
                required
                minLength={1}
                value={address.street}
                onChange={(e) =>
                  setAddress((prev) => ({ ...prev, street: e.target.value }))
                }
                className={inputClass}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-stone-700">City</label>
              <input
                type="text"
                required
                minLength={1}
                value={address.city}
                onChange={(e) =>
                  setAddress((prev) => ({ ...prev, city: e.target.value }))
                }
                className={inputClass}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-stone-700">State</label>
              <input
                type="text"
                required
                minLength={1}
                value={address.state}
                onChange={(e) =>
                  setAddress((prev) => ({ ...prev, state: e.target.value }))
                }
                className={inputClass}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-stone-700">
                Pincode (6 digits)
              </label>
              <input
                type="text"
                required
                pattern="\d{6}"
                maxLength={6}
                value={address.pincode}
                onChange={(e) =>
                  setAddress((prev) => ({ ...prev, pincode: e.target.value }))
                }
                className={inputClass}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </form>
      </div>
    </div>
  );
}
