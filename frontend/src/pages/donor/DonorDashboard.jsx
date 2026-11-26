import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../api/client';
import StatusBadge from '../../components/StatusBadge';
import { PlusCircle, Clock, MapPin, AlertCircle, XCircle } from 'lucide-react';

export default function DonorDashboard() {
  const [donations, setDonations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(null);

  const fetchDonations = async () => {
    setLoading(true);
    try {
      const res = await api.donor.getMyDonations();
      setDonations(res.items || []);
    } catch (err) {
      setError(err.detail || 'Failed to load your donations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDonations();
  }, []);

  const handleCancel = async (id) => {
    if (!window.confirm('Are you sure you want to cancel this donation?')) return;
    setActionLoading(id);
    try {
      await api.donor.cancelDonation(id);
      await fetchDonations();
    } catch (err) {
      alert(err.detail || 'Failed to cancel donation');
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Donor Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">Manage and track your surplus food listings</p>
        </div>
        <Link
          to="/donor/create"
          className="inline-flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-4 py-2.5 rounded-lg shadow-sm text-sm"
        >
          <PlusCircle className="w-4 h-4" />
          <span>New Food Donation</span>
        </Link>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-lg text-sm text-rose-700 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center items-center py-20">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
        </div>
      ) : donations.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-slate-200 p-8">
          <p className="text-slate-500 text-base">You haven't posted any food donations yet.</p>
          <Link
            to="/donor/create"
            className="mt-4 inline-flex items-center gap-2 text-emerald-600 font-semibold hover:underline text-sm"
          >
            <PlusCircle className="w-4 h-4" />
            Post your first donation now
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {donations.map((d) => (
            <div
              key={d.id}
              className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow transition flex flex-col justify-between"
            >
              <div>
                <div className="flex justify-between items-start gap-2 mb-3">
                  <h3 className="font-bold text-slate-900 text-lg leading-snug">{d.title}</h3>
                  <StatusBadge status={d.status} />
                </div>

                <div className="space-y-2 text-sm text-slate-600 mb-4">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-800">
                      {d.quantity} {d.quantity_unit}
                    </span>
                    <span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded uppercase font-semibold">
                      {d.food_type}
                    </span>
                  </div>

                  {d.description && <p className="text-slate-500 text-xs italic">{d.description}</p>}

                  <div className="flex items-start gap-1.5 text-xs text-slate-500 pt-1">
                    <MapPin className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />
                    <span>
                      {d.pickup_address?.street}, {d.pickup_address?.city},{' '}
                      {d.pickup_address?.pincode}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 text-xs text-slate-500">
                    <Clock className="w-4 h-4 text-slate-400 flex-shrink-0" />
                    <span>Expires: {new Date(d.expires_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="border-t border-slate-100 pt-3 flex justify-between items-center text-xs">
                <span className="text-slate-400">
                  Posted {new Date(d.created_at).toLocaleDateString()}
                </span>
                {d.status === 'AVAILABLE' && (
                  <button
                    onClick={() => handleCancel(d.id)}
                    disabled={actionLoading === d.id}
                    className="inline-flex items-center gap-1 text-rose-600 hover:text-rose-700 font-medium"
                  >
                    <XCircle className="w-4 h-4" />
                    {actionLoading === d.id ? 'Cancelling...' : 'Cancel'}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
