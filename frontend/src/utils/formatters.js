/**
 * Formatting helpers for FoodShare
 */

export function getExpiryCountdown(expiresAt) {
  const now = new Date();
  const expiry = new Date(expiresAt);
  const diffMs = expiry.getTime() - now.getTime();

  if (diffMs <= 0) {
    return {
      label: 'Expired',
      isExpired: true,
      isUrgent: false,
      badgeClass: 'bg-zinc-100 text-zinc-600 border-zinc-200',
    };
  }

  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

  if (diffHours < 2) {
    return {
      label: `Expires in ${diffMinutes}m (URGENT)`,
      isExpired: false,
      isUrgent: true,
      badgeClass: 'bg-rose-100 text-rose-800 border-rose-300 font-bold',
    };
  }

  if (diffHours < 6) {
    return {
      label: `Expires in ${diffHours}h ${diffMinutes}m`,
      isExpired: false,
      isUrgent: true,
      badgeClass: 'bg-amber-100 text-amber-800 border-amber-300 font-semibold',
    };
  }

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays > 0) {
    return {
      label: `Expires in ${diffDays}d ${diffHours % 24}h`,
      isExpired: false,
      isUrgent: false,
      badgeClass: 'bg-slate-100 text-slate-700 border-slate-200',
    };
  }

  return {
    label: `Expires in ${diffHours}h ${diffMinutes}m`,
    isExpired: false,
    isUrgent: false,
    badgeClass: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  };
}
