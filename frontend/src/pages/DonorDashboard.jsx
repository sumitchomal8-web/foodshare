import { useEffect, useState } from "react";
import { formatApiError } from "../api/client";
import {
  cancelDonation,
  createDonation,
  getMyDonations,
  updateDonation,
} from "../api/donations";
import ErrorMessage from "../components/ErrorMessage";
import Loading from "../components/Loading";
import Pagination from "../components/Pagination";
import StatusBadge from "../components/StatusBadge";
import { useAuth } from "../context/AuthContext";

const FOOD_TYPES = [
  "COOKED_MEALS",
  "RAW_INGREDIENTS",
  "PACKAGED_FOOD",
  "BAKERY",
  "FRUITS_VEGETABLES",
];

const STATUS_OPTIONS = [
  "ALL",
  "AVAILABLE",
  "ACCEPTED",
  "PICKED_UP",
  "DISTRIBUTED",
  "COMPLETED",
  "CANCELLED",
  "EXPIRED",
];

function toLocalInputValue(date) {
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60000);
  return local.toISOString().slice(0, 16);
}

function getExpiryInfo(expiresAt) {
  const diffMs = new Date(expiresAt).getTime() - Date.now();
  if (diffMs <= 0) {
    return { label: "Expired", urgent: false, expired: true };
  }
  const totalMinutes = Math.floor(diffMs / 60000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours < 2) {
    const label = hours > 0 ? `${hours}h ${minutes}m left` : `${minutes}m left`;
    return { label, urgent: true, expired: false };
  }
  if (hours < 24) {
    return { label: `${hours}h ${minutes}m left`, urgent: false, expired: false };
  }
  const days = Math.floor(hours / 24);
  return { label: `${days}d ${hours % 24}h left`, urgent: false, expired: false };
}

export default function DonorDashboard() {
  const { user } = useAuth();
  const [donations, setDonations] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [confirmCancelId, setConfirmCancelId] = useState(null);
  const [expandedHistoryIds, setExpandedHistoryIds] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const buildEmptyForm = () => {
    const now = new Date();
    const sixHoursLater = new Date(now.getTime() + 6 * 60 * 60 * 1000);
    return {
      title: "",
      food_type: "COOKED_MEALS",
      quantity: 10,
      quantity_unit: "servings",
      description: "",
      pickup_address: user?.address
        ? { ...user.address }
        : { street: "", city: "", state: "", pincode: "" },
      available_from: toLocalInputValue(now),
      expires_at: toLocalInputValue(sixHoursLater),
    };
  };

  const [form, setForm] = useState(buildEmptyForm);

  const loadDonations = async (targetPage = page, targetStatus = statusFilter) => {
    setLoading(true);
    setError("");
    try {
      const params = { page: targetPage, limit: 9 };
      if (targetStatus !== "ALL") {
        params.status = targetStatus;
      }
      const data = await getMyDonations(params);
      setDonations(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDonations(page, statusFilter);
  }, [page, statusFilter]);

  const openCreateForm = () => {
    setEditingId(null);
    setForm(buildEmptyForm());
    setShowForm(true);
    setError("");
    setSuccess("");
  };

  const openEditForm = (item) => {
    setEditingId(item.id);
    setForm({
      title: item.title,
      food_type: item.food_type,
      quantity: item.quantity,
      quantity_unit: item.quantity_unit,
      description: item.description || "",
      pickup_address: { ...item.pickup_address },
      available_from: toLocalInputValue(new Date(item.available_from)),
      expires_at: toLocalInputValue(new Date(item.expires_at)),
    });
    setShowForm(true);
    setError("");
    setSuccess("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setSubmitting(true);

    const payload = {
      title: form.title,
      food_type: form.food_type,
      quantity: Number(form.quantity),
      quantity_unit: form.quantity_unit,
      description: form.description.trim() || null,
      pickup_address: form.pickup_address,
      available_from: new Date(form.available_from).toISOString(),
      expires_at: new Date(form.expires_at).toISOString(),
    };

    try {
      if (editingId) {
        await updateDonation(editingId, payload);
        setSuccess("Donation updated.");
      } else {
        await createDonation(payload);
        setSuccess("Donation posted! Nearby verified NGOs can now accept it.");
      }
      setShowForm(false);
      setEditingId(null);
      await loadDonations(1, statusFilter);
      setPage(1);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancelDonation = async (id) => {
    setError("");
    setSuccess("");
    try {
      await cancelDonation(id);
      setConfirmCancelId(null);
      setSuccess("Donation cancelled.");
      await loadDonations(page, statusFilter);
    } catch (err) {
      setError(formatApiError(err));
    }
  };

  const toggleHistory = (id) => {
    setExpandedHistoryIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const availableCount = donations.filter((d) => d.status === "AVAILABLE").length;
  const completedCount = donations.filter((d) => d.status === "COMPLETED").length;

  const inputClass =
    "mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-stone-900">Donor Dashboard</h1>
          <p className="text-sm text-stone-600">
            Post surplus food and track pickup progress.
          </p>
        </div>

        <button
          type="button"
          onClick={() => (showForm ? setShowForm(false) : openCreateForm())}
          className="rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700"
        >
          {showForm ? "Close Form" : "+ Post Food Donation"}
        </button>
      </div>

      <ErrorMessage message={error} onDismiss={() => setError("")} />
      {success && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          {success}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-stone-500">
            {statusFilter === "ALL" ? "Total Donations" : `Total (${statusFilter})`}
          </p>
          <p className="mt-1 text-2xl font-bold text-stone-900">{total}</p>
        </div>
        <div className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-stone-500">
            Available (This Page)
          </p>
          <p className="mt-1 text-2xl font-bold text-emerald-700">{availableCount}</p>
        </div>
        <div className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wide text-stone-500">
            Completed (This Page)
          </p>
          <p className="mt-1 text-2xl font-bold text-stone-900">{completedCount}</p>
        </div>
      </div>

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-stone-200 bg-white p-6 shadow-sm space-y-4"
        >
          <h2 className="text-lg font-semibold text-stone-900">
            {editingId ? "Edit Donation" : "New Food Donation"}
          </h2>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-stone-700">Title</label>
              <input
                type="text"
                required
                minLength={3}
                maxLength={120}
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="e.g. Fresh Veg Pulao from Community Event"
                className={inputClass}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-stone-700">Food Type</label>
              <select
                value={form.food_type}
                onChange={(e) => setForm({ ...form, food_type: e.target.value })}
                className={inputClass}
              >
                {FOOD_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-stone-700">Quantity</label>
                <input
                  type="number"
                  required
                  min="0.1"
                  step="any"
                  value={form.quantity}
                  onChange={(e) => setForm({ ...form, quantity: e.target.value })}
                  className={inputClass}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-stone-700">Unit</label>
                <input
                  type="text"
                  required
                  minLength={1}
                  value={form.quantity_unit}
                  onChange={(e) => setForm({ ...form, quantity_unit: e.target.value })}
                  placeholder="servings / kg"
                  className={inputClass}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-stone-700">
                Available From
              </label>
              <input
                type="datetime-local"
                required
                value={form.available_from}
                onChange={(e) => setForm({ ...form, available_from: e.target.value })}
                className={inputClass}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-stone-700">
                Expires At
              </label>
              <input
                type="datetime-local"
                required
                value={form.expires_at}
                onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
                className={inputClass}
              />
            </div>

            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-stone-700">
                Description (Optional)
              </label>
              <textarea
                rows={2}
                maxLength={1000}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Packaging notes, allergen info, or pickup instructions..."
                className={inputClass}
              />
            </div>
          </div>

          <div className="border-t border-stone-200 pt-4">
            <h3 className="text-sm font-semibold text-stone-800">Pickup Address</h3>
            <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <input
                  type="text"
                  required
                  minLength={1}
                  placeholder="Street"
                  value={form.pickup_address.street}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      pickup_address: { ...form.pickup_address, street: e.target.value },
                    })
                  }
                  className={inputClass}
                />
              </div>
              <input
                type="text"
                required
                minLength={1}
                placeholder="City"
                value={form.pickup_address.city}
                onChange={(e) =>
                  setForm({
                    ...form,
                    pickup_address: { ...form.pickup_address, city: e.target.value },
                  })
                }
                className={inputClass}
              />
              <input
                type="text"
                required
                minLength={1}
                placeholder="State"
                value={form.pickup_address.state}
                onChange={(e) =>
                  setForm({
                    ...form,
                    pickup_address: { ...form.pickup_address, state: e.target.value },
                  })
                }
                className={inputClass}
              />
              <input
                type="text"
                required
                pattern="\d{6}"
                maxLength={6}
                placeholder="6-digit Pincode"
                value={form.pickup_address.pincode}
                onChange={(e) =>
                  setForm({
                    ...form,
                    pickup_address: { ...form.pickup_address, pincode: e.target.value },
                  })
                }
                className={inputClass}
              />
            </div>
          </div>

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-emerald-600 px-5 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60"
            >
              {submitting
                ? "Saving..."
                : editingId
                  ? "Save Changes"
                  : "Post Donation"}
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="rounded-lg border border-stone-300 px-4 py-2 text-sm font-medium text-stone-700 hover:bg-stone-50"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-stone-900">My Donations</h2>
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value);
            setPage(1);
          }}
          className="rounded-lg border border-stone-300 bg-white px-3 py-1.5 text-sm text-stone-700"
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s === "ALL" ? "All Statuses" : s}
            </option>
          ))}
        </select>
      </div>

      {loading ? (
        <Loading message="Loading your donations..." />
      ) : donations.length === 0 ? (
        <div className="rounded-xl border border-dashed border-stone-300 bg-white p-10 text-center text-sm text-stone-600">
          No donations found for this filter. Click{" "}
          <span className="font-semibold text-emerald-700">+ Post Food Donation</span>{" "}
          to share surplus food.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {donations.map((item) => {
            const expiry = getExpiryInfo(item.expires_at);
            const historyOpen = Boolean(expandedHistoryIds[item.id]);

            return (
              <div
                key={item.id}
                className="flex flex-col justify-between rounded-xl border border-stone-200 bg-white p-5 shadow-sm"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-semibold text-stone-900">{item.title}</h3>
                    <StatusBadge status={item.status} />
                  </div>
                  <p className="mt-1 text-xs font-medium text-emerald-700">
                    {item.food_type.replaceAll("_", " ")} • {item.quantity}{" "}
                    {item.quantity_unit}
                  </p>
                  {item.description && (
                    <p className="mt-2 text-sm text-stone-600">{item.description}</p>
                  )}
                  <div className="mt-3 space-y-1 text-xs text-stone-500">
                    <p>
                      Pickup: {item.pickup_address.street}, {item.pickup_address.city},{" "}
                      {item.pickup_address.state} ({item.pickup_address.pincode})
                    </p>
                    <p className="flex flex-wrap items-center gap-2">
                      <span>Expires: {new Date(item.expires_at).toLocaleString()}</span>
                      {item.status === "AVAILABLE" && (
                        <span
                          className={`rounded-full px-2 py-0.5 font-semibold ${
                            expiry.urgent
                              ? "bg-amber-100 text-amber-800"
                              : expiry.expired
                                ? "bg-stone-200 text-stone-700"
                                : "bg-stone-100 text-stone-600"
                          }`}
                        >
                          {expiry.label}
                        </span>
                      )}
                    </p>
                    <div className="flex items-center gap-4 pt-1">
                      <a
                        href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
                          `${item.pickup_address.street}, ${item.pickup_address.city}, ${item.pickup_address.state} ${item.pickup_address.pincode}`
                        )}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-semibold text-emerald-700 hover:underline"
                      >
                        View Pickup on Map ↗
                      </a>
                      {item.status_history?.length > 0 && (
                        <button
                          type="button"
                          onClick={() => toggleHistory(item.id)}
                          className="font-semibold text-stone-600 hover:text-stone-900"
                        >
                          {historyOpen
                            ? "Hide History"
                            : `History (${item.status_history.length})`}
                        </button>
                      )}
                    </div>
                  </div>

                  {historyOpen && item.status_history?.length > 0 && (
                    <div className="mt-3 space-y-2 border-t border-stone-100 pt-3">
                      {item.status_history.map((entry, idx) => (
                        <div
                          key={`${item.id}-hist-${idx}`}
                          className="flex items-center justify-between gap-2 text-xs"
                        >
                          <StatusBadge status={entry.status} />
                          <span className="text-stone-500">
                            {new Date(entry.changed_at).toLocaleString()}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {item.status === "AVAILABLE" && (
                  <div className="mt-4 border-t border-stone-100 pt-3">
                    {confirmCancelId === item.id ? (
                      <div className="flex items-center justify-between gap-2 rounded-lg bg-rose-50 px-3 py-2">
                        <span className="text-xs font-medium text-rose-800">
                          Cancel this donation?
                        </span>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => handleCancelDonation(item.id)}
                            className="rounded-md bg-rose-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-rose-700"
                          >
                            Confirm
                          </button>
                          <button
                            type="button"
                            onClick={() => setConfirmCancelId(null)}
                            className="rounded-md border border-stone-300 bg-white px-2.5 py-1 text-xs font-semibold text-stone-700 hover:bg-stone-50"
                          >
                            Keep
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => openEditForm(item)}
                          className="flex-1 rounded-lg border border-stone-300 px-3 py-1.5 text-xs font-semibold text-stone-700 hover:bg-stone-50"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => setConfirmCancelId(item.id)}
                          className="flex-1 rounded-lg border border-rose-200 bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 hover:bg-rose-100"
                        >
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <Pagination
        page={page}
        limit={9}
        total={total}
        onPageChange={(newPage) => setPage(newPage)}
      />
    </div>
  );
}
