const STATUS_STYLES = {
  AVAILABLE: "bg-emerald-100 text-emerald-800",
  VERIFIED: "bg-emerald-100 text-emerald-800",
  COMPLETED: "bg-emerald-100 text-emerald-800",
  PENDING: "bg-amber-100 text-amber-800",
  ACCEPTED: "bg-amber-100 text-amber-800",
  PICKED_UP: "bg-sky-100 text-sky-800",
  DISTRIBUTED: "bg-indigo-100 text-indigo-800",
  CANCELLED: "bg-stone-200 text-stone-700",
  EXPIRED: "bg-stone-200 text-stone-700",
  REJECTED: "bg-rose-100 text-rose-800",
};

export default function StatusBadge({ status }) {
  const style = STATUS_STYLES[status] || "bg-stone-100 text-stone-700";
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${style}`}
    >
      {status}
    </span>
  );
}
