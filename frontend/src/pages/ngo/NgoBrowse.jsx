import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import StatusBadge from '../../components/StatusBadge';
import { useToast } from '../../context/ToastContext';
import { getExpiryCountdown } from '../../utils/formatters';
import { Search, MapPin, Clock, AlertTriangle, Utensils } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function NgoBrowse() {
  const { isVerifiedNgo } = useAuth();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [donations, setDonations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [cityFilter, setCityFilter] = useState('');
  const [foodTypeFilter, setFoodTypeFilter] = useState('');
  const [acceptingId, setAcceptingId] = useState(null);

  const fetchAvailable = async () => {
    setLoading(true);
    setError('');
    try {
      const params = { status: 'AVAILABLE' };
      if (cityFilter.trim()) params.city = cityFilter.trim();
      if (foodTypeFilter) params.food_type = foodTypeFilter;

      const res = await api.donations.browse(params);
      setDonations(res.items || []);
    } catch (err) {
      setError(err.detail || 'Failed to fetch available donations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAvailable();
  }, [foodTypeFilter]);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchAvailable();
  };

  const handleAccept = async (donation) => {
    if (!isVerifiedNgo) {
      showToast('Your organization must be verified by an admin before accepting donations.', 'warning');
      return;
    }

    if (!window.confirm(`Accept donation "${donation.title}"? You will be assigned to pick it up.`)) {
      return;
    }

    setAcceptingId(donation.id);
    try {
      await api.donations.accept(donation.id);
      showToast(`Successfully claimed "${donation.title}"! Redirecting...`, 'success');
      navigate('/ngo/deliveries');
    } catch (err) {
      showToast(err.detail || 'Could not accept donation. It may have been claimed or expired.', 'error');
      await fetchAvailable();
    } finally {
      setAcceptingId(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Browse Available Food Donations</h1>
        <p className="text-sm text-slate-500 mt-1">Claim surplus food listings from local donors</p>
      </div>

      {/* Verification Warning Banner */}
      {!isVerifiedNgo && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-3 text-sm text-amber-800">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Account Verification Pending: </span>
            Your NGO registration is currently under review by platform administrators. You can browse all available donations, but you cannot accept them until verified.
          </div>
        </div>
      )}

      {/* Filter Bar */}
      <form
        onSubmit={handleSearch}
        className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row gap-3 items-center"
      >
        <div className="relative flex-1 w-full">
          <MapPin className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            value={cityFilter}
            onChange={(e) => setCityFilter(e.target.value)}
            placeholder="Filter by city (e.g. Mumbai, Delhi)..."
            className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-emerald-500"
          />
        </div>

        <select
          value={foodTypeFilter}
          onChange={(e) => setFoodTypeFilter(e.target.value)}
          className="w-full sm:w-48 px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-emerald-500"
        >
          <option value="">All Food Types</option>
          <option value="COOKED">Cooked</option>
          <option value="PACKAGED">Packaged</option>
          <option value="RAW">Raw</option>
          <option value="BAKERY">Bakery</option>
          <option value="OTHER">Other</option>
        </select>

        <button
          type="submit"
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-5 py-2 rounded-lg text-sm shadow-sm"
        >
          <Search className="w-4 h-4" />
          <span>Filter</span>
        </button>
      </form>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-lg text-sm text-rose-700">
          {error}
        </div>
      )}

      {/* Grid of Donations */}
      {loading ? (
        <div className="flex justify-center items-center py-20">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
        </div>
      ) : donations.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-slate-200 p-8">
          <Utensils className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-600 font-medium text-base">No available donations found.</p>
          <p className="text-slate-400 text-xs mt-1">Try adjusting your city or food type filter.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {donations.map((d) => {
            const expiry = getExpiryCountdown(d.expires_at);
            return (
              <div
                key={d.id}
                className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow transition flex flex-col justify-between"
              >
                <div>
                  <div className="flex justify-between items-start gap-2 mb-2">
                    <h3 className="font-bold text-slate-900 text-lg leading-snug">{d.title}</h3>
                    <StatusBadge status={d.status} />
                  </div>

                  <div className="space-y-2 text-sm text-slate-600 mb-4">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded text-sm">
                        {d.quantity} {d.quantity_unit}
                      </span>
                      <span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded uppercase font-semibold">
                        {d.food_type}
                      </span>
                    </div>

                    {d.description && <p className="text-slate-500 text-xs">{d.description}</p>}

                    {d.food_image_url && (
                      <a href={d.food_image_url} target="_blank" rel="noopener noreferrer" className="block pt-1">
                        <img
                          src={d.food_image_url}
                          alt={d.title}
                          className="h-32 w-full rounded-lg object-cover border border-slate-200"
                        />
                      </a>
                    )}

                    <div className="flex items-start gap-1.5 text-xs text-slate-500 pt-1">
                      <MapPin className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />
                      <span>
                        {d.pickup_address?.street}, {d.pickup_address?.city} ({d.pickup_address?.pincode})
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-xs pt-1">
                      <div className="flex items-center gap-1.5 text-slate-500">
                        <Clock className="w-4 h-4 text-slate-400 flex-shrink-0" />
                        <span>{new Date(d.expires_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${expiry.badgeClass}`}>
                        {expiry.label}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Action Button */}
                <div className="border-t border-slate-100 pt-3">
                  <button
                    onClick={() => handleAccept(d)}
                    disabled={!isVerifiedNgo || acceptingId === d.id}
                    className={`w-full py-2 px-4 rounded-lg font-semibold text-sm transition shadow-sm ${
                      !isVerifiedNgo
                        ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                        : 'bg-emerald-600 hover:bg-emerald-700 text-white'
                    }`}
                  >
                    {acceptingId === d.id
                      ? 'Claiming...'
                      : !isVerifiedNgo
                      ? 'Verification Required'
                      : 'Accept Donation'}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
