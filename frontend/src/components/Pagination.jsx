export default function Pagination({ page, limit, total, onPageChange }) {
  const totalPages = Math.max(1, Math.ceil(total / limit));
  if (total <= limit && page === 1) return null;

  return (
    <div className="mt-6 flex items-center justify-between border-t border-stone-200 pt-4 text-sm">
      <p className="text-stone-600">
        Page <span className="font-semibold text-stone-900">{page}</span> of{" "}
        <span className="font-semibold text-stone-900">{totalPages}</span> ({total} total)
      </p>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="rounded-lg border border-stone-300 bg-white px-3 py-1.5 font-medium text-stone-700 hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Previous
        </button>
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          className="rounded-lg border border-stone-300 bg-white px-3 py-1.5 font-medium text-stone-700 hover:bg-stone-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}
