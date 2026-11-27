import { useAuth } from "../context/AuthContext";

export default function NgoVerificationBanner() {
  const { user, isAuthenticated } = useAuth();

  if (!isAuthenticated || user?.role !== "NGO" || !user?.ngo_profile) {
    return null;
  }

  const status = user.ngo_profile.verification_status;
  if (status === "VERIFIED") {
    return null;
  }

  if (status === "REJECTED") {
    return (
      <div className="mb-6 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
        <span className="font-semibold">Verification Rejected:</span> Your NGO
        account was not approved by an administrator. Please contact support for
        details.
      </div>
    );
  }

  return (
    <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
      <span className="font-semibold">Pending Verification:</span> Your NGO
      account is awaiting admin approval. You can update your profile now, and
      you&apos;ll be able to accept donations once verified.
    </div>
  );
}
