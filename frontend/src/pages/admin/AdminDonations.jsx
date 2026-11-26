import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import StatusBadge from '../../components/StatusBadge';
import { Utensils, AlertCircle } from 'lucide-react';

export default function AdminDonations() {
  const [donations, setDonations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [foodTypeFilter, setFoodTypeFilter] = useState('');
  const [error, setError] = useState('');

  const fetchDonations = async () => {
    setLoading(true);
    setError('');
    try {
      const params = {};
      if (statusFilter) params.status = statusFilter;
      if (foodTypeFilter) params.food_type = foodTypeFilter;

      const res = await api.admin.getDonations(params);
      setDonations(res.items || []);
    } catch (err) {
      setError(err.detail || 'Failed to fetch platform donations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDonations();
  }, [statusFilter, foodTypeFilter]);

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">All Platform Donations</h1>
          <p className="text-sm text-slate-500 mt-1">Audit and oversee all surplus food listings across all statuses</p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-semibold"
          >
            <option value="">All Statuses</option>
            <option value="AVAILABLE">Available</option>
            <option value="ACCEPTED">Accepted</option>
            <option value="PICKED_UP">Picked Up</option>
            <option value="DISTRIBUTED">Distributed</option>
            <option value="COMPLETED">Completed</option>
            <option value="CANCELLED">Cancelled</option>
            <option value="EXPIRED">Expired</option>
          </select>

          <select
            value={foodTypeFilter}
            onChange={(e) => setFoodTypeFilter(e.target.value)}
            className="px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-semibold"
          >
            <option value="">All Food Types</option>
            <option value="COOKED">Cooked</option>
            <option value="PACKAGED">Packaged</option>
            <option value="RAW">Raw</option>
            <option value="BAKERY">Bakery</option>
            <option value="OTHER">Other</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-lg text-sm text-rose-700">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center items-center py-20">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
        </div>
      ) : donations.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-slate-200 p-8">
          <Utensils className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-600 font-medium text-base">No donations match your selected filters.</p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-slate-500 font-semibold text-xs uppercase text-left">
              <tr>
                <th className="px-6 py-3">Donation Title</th>
                <th className="px-6 py-3">Type & Quantity</th>
                <th className="px-6 py-3">Location</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Created / Expires</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {donations.map((d) => (
                <tr key={d.id} className="hover:bg-slate-50/50">
                  <td className="px-6 py-4">
                    <div className="font-bold text-slate-900">{d.title}</div>
                    {d.description && <div className="text-xs text-slate-400 truncate max-w-xs">{d.description}</div>}
                  </td>
                  <td className="px-6 py-4">
                    <div className="font-semibold text-slate-800">
                      {d.quantity} {d.quantity_unit}
                    </div>
                    <span className="text-xs text-slate-500 uppercase">{d.food_type}</span>
                  </td>
                  <td className="px-6 py-4 text-xs text-slate-600">
                    <div>{d.pickup_address?.street}</div>
                    <div className="text-slate-400">{d.pickup_address?.city} ({d.pickup_address?.pincode})</div>
                  </td>
                  <td className="px-6 py-4">
                    <StatusBadge status={d.status} />
                  </td>
                  <td className="px-6 py-4 text-xs text-slate-500">
                    <div>Posted: {new Date(d.created_at).toLocaleDateString()}</div>
                    <div className="text-slate-400">Expires: {new Date(d.expires_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
