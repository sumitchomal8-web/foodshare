import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { formatApiError } from "../api/client";
import ErrorMessage from "../components/ErrorMessage";
import { useAuth } from "../context/AuthContext";

const INITIAL_ADDRESS = {
  street: "",
  city: "",
  state: "",
  pincode: "",
};

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [phone, setPhone] = useState("");
  const [role, setRole] = useState("DONOR");
  const [address, setAddress] = useState(INITIAL_ADDRESS);

  const [orgName, setOrgName] = useState("");
  const [orgType, setOrgType] = useState("NGO");
  const [registrationNumber, setRegistrationNumber] = useState("");

  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleAddressChange = (field, value) => {
    setAddress((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    const payload = {
      name,
      email,
      password,
      phone,
      role,
      address,
      ngo_profile:
        role === "NGO"
          ? {
              organization_name: orgName,
              org_type: orgType,
              registration_number:
                orgType === "NGO" ? registrationNumber : registrationNumber || null,
            }
          : null,
    };

    try {
      await register(payload);
      navigate("/login", {
        replace: true,
        state: {
          message:
            role === "NGO"
              ? "NGO account created! Sign in now (an admin will verify your organization)."
              : "Account created successfully! Please sign in.",
        },
      });
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSubmitting(false);
    }
  };

  const inputClass =
    "mt-1 w-full rounded-lg border border-stone-300 px-3 py-2 text-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500";

  return (
    <div className="mx-auto mt-4 max-w-2xl rounded-xl border border-stone-200 bg-white p-6 shadow-sm">
      <h1 className="text-2xl font-bold text-stone-900">Create your FoodShare account</h1>
      <p className="mt-1 text-sm text-stone-600">
        Join as a food donor or an NGO / volunteer organization.
      </p>

      <div className="mt-4">
        <ErrorMessage message={error} onDismiss={() => setError("")} />
      </div>

      <form onSubmit={handleSubmit} className="mt-4 space-y-5">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-stone-700">Account Type</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className={inputClass}
            >
              <option value="DONOR">Donor (Share surplus food)</option>
              <option value="NGO">NGO / Volunteer (Rescue food)</option>
            </select>
          </div>

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
            <label className="block text-sm font-medium text-stone-700">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
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
            <label className="block text-sm font-medium text-stone-700">
              Password (8–72 characters)
            </label>
            <input
              type="password"
              required
              minLength={8}
              maxLength={72}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputClass}
            />
          </div>
        </div>

        <div className="border-t border-stone-200 pt-4">
          <h2 className="text-sm font-semibold text-stone-800">Address</h2>
          <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-stone-700">Street</label>
              <input
                type="text"
                required
                minLength={1}
                value={address.street}
                onChange={(e) => handleAddressChange("street", e.target.value)}
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
                onChange={(e) => handleAddressChange("city", e.target.value)}
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
                onChange={(e) => handleAddressChange("state", e.target.value)}
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
                onChange={(e) => handleAddressChange("pincode", e.target.value)}
                placeholder="560001"
                className={inputClass}
              />
            </div>
          </div>
        </div>

        {role === "NGO" && (
          <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-4">
            <h2 className="text-sm font-semibold text-stone-800">
              Organization Details
            </h2>
            <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <label className="block text-sm font-medium text-stone-700">
                  Organization Name
                </label>
                <input
                  type="text"
                  required
                  minLength={1}
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  className={inputClass}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-stone-700">
                  Organization Type
                </label>
                <select
                  value={orgType}
                  onChange={(e) => setOrgType(e.target.value)}
                  className={inputClass}
                >
                  <option value="NGO">Registered NGO</option>
                  <option value="VOLUNTEER">Volunteer Group</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-stone-700">
                  Registration Number{" "}
                  {orgType === "NGO" ? "(Required)" : "(Optional)"}
                </label>
                <input
                  type="text"
                  required={orgType === "NGO"}
                  value={registrationNumber}
                  onChange={(e) => setRegistrationNumber(e.target.value)}
                  className={inputClass}
                />
              </div>
            </div>
          </div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? "Creating account..." : "Create Account"}
        </button>
      </form>

      <p className="mt-5 text-center text-sm text-stone-600">
        Already registered?{" "}
        <Link to="/login" className="font-semibold text-emerald-700 hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
