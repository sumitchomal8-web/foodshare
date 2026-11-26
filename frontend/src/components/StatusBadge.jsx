import React from 'react';

const statusConfig = {
  AVAILABLE: { bg: 'bg-emerald-100 text-emerald-800 border-emerald-300', label: 'Available' },
  ACCEPTED: { bg: 'bg-blue-100 text-blue-800 border-blue-300', label: 'Accepted' },
  PICKED_UP: { bg: 'bg-amber-100 text-amber-800 border-amber-300', label: 'Picked Up' },
  DISTRIBUTED: { bg: 'bg-purple-100 text-purple-800 border-purple-300', label: 'Distributed' },
  COMPLETED: { bg: 'bg-slate-100 text-slate-800 border-slate-300', label: 'Completed' },
  CANCELLED: { bg: 'bg-rose-100 text-rose-800 border-rose-300', label: 'Cancelled' },
  EXPIRED: { bg: 'bg-zinc-100 text-zinc-600 border-zinc-300', label: 'Expired' },

  // Verification statuses
  VERIFIED: { bg: 'bg-emerald-100 text-emerald-800 border-emerald-300', label: 'Verified' },
  PENDING: { bg: 'bg-amber-100 text-amber-800 border-amber-300', label: 'Pending Verification' },
  REJECTED: { bg: 'bg-rose-100 text-rose-800 border-rose-300', label: 'Rejected' },
};

export default function StatusBadge({ status }) {
  const config = statusConfig[status] || {
    bg: 'bg-gray-100 text-gray-800 border-gray-300',
    label: status,
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${config.bg}`}
    >
      {config.label}
    </span>
  );
}
