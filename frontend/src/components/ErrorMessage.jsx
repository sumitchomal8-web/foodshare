export default function ErrorMessage({ message, onDismiss }) {
  if (!message) return null;

  return (
    <div className="mb-4 flex items-start justify-between gap-3 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
      <span>{message}</span>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="font-semibold text-rose-600 hover:text-rose-900"
        >
          ✕
        </button>
      )}
    </div>
  );
}
