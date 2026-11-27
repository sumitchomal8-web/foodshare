export default function Loading({ message = "Loading..." }) {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="flex items-center gap-3 text-stone-600">
        <span className="h-5 w-5 animate-spin rounded-full border-2 border-emerald-600 border-t-transparent" />
        <span className="text-sm font-medium">{message}</span>
      </div>
    </div>
  );
}
