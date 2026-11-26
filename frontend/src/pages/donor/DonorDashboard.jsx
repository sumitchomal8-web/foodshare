import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../api/client';
import StatusBadge from '../../components/StatusBadge';
import { useToast } from '../../context/ToastContext';
import { getExpiryCountdown } from '../../utils/formatters';
import { PlusCircle, Clock, MapPin, AlertCircle, XCircle, Edit3, X, Check } from 'lucide-react';

export default function DonorDashboard() {
  const [donations, setDonations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(null);

  // Edit Modal State
  const [editingDonation, setEditingDonation] = useState(null);
  const [editForm, setEditForm] = useState({
    title: '',
    quantity: '',
    quantity_unit: 'PLATES',
    description: '',
  });
  const [editSaving, setEditSaving] = useState(false);

  const { showToast } = useToast();

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
      showToast('Donation cancelled successfully', 'info');
      await fetchDonations();
    } catch (err) {
      showToast(err.detail || 'Failed to cancel donation', 'error');
    } finally {
      setActionLoading(null);
    }
  };

  const openEditModal = (donation) => {
    setEditingDonation(donation);
    setEditForm({
      title: donation.title,
      quantity: donation.quantity,
      quantity_unit: donation.quantity_unit,
      description: donation.description || '',
    });
  };

  const handleSaveEdit = async (e) => {
    e.preventDefault();
    if (!editingDonation) return;

    setEditSaving(true);
    try {
      const payload = {
        title: editForm.title,
        quantity: Number(editForm.quantity),
        quantity_unit: editForm.quantity_unit,
        description: editForm.description || null,
      };

      await api.donor.updateDonation(editingDonation.id, payload);
      showToast('Donation updated successfully', 'success');
      setEditingDonation(null);
      await fetchDonations();
    } catch (err) {
      showToast(err.detail || 'Failed to update donation', 'error');
    } finally {
      setEditSaving(false);
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
          {donations.map((d) => {
            const expiry = getExpiryCountdown(d.expires_at);
            return (
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

                {/* Actions */}
                <div className="border-t border-slate-100 pt-3 flex justify-between items-center text-xs">
                  <span className="text-slate-400">
                    Posted {new Date(d.created_at).toLocaleDateString()}
                  </span>
                  {d.status === 'AVAILABLE' && (
                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => openEditModal(d)}
                        className="inline-flex items-center gap-1 text-slate-600 hover:text-emerald-600 font-medium"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                        <span>Edit</span>
                      </button>
                      <button
                        onClick={() => handleCancel(d.id)}
                        disabled={actionLoading === d.id}
                        className="inline-flex items-center gap-1 text-rose-600 hover:text-rose-700 font-medium"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        <span>{actionLoading === d.id ? 'Cancelling...' : 'Cancel'}</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Edit Donation Modal */}
      {editingDonation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200">
            <div className="flex justify-between items-center mb-4 border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-lg">Edit Donation Listing</h3>
              <button
                onClick={() => setEditingDonation(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveEdit} className="space-y-4 text-sm">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                  Title
                </label>
                <input
                  type="text"
                  required
                  value={editForm.title}
                  onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                    Quantity
                  </label>
                  <input
                    type="number"
                    min="0.1"
                    step="any"
                    required
                    value={editForm.quantity}
                    onChange={(e) => setEditForm({ ...editForm, quantity: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                    Unit
                  </label>
                  <select
                    value={editForm.quantity_unit}
                    onChange={(e) => setEditForm({ ...editForm, quantity_unit: e.target.value })}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-emerald-500"
                  >
                    <option value="PLATES">Plates</option>
                    <option value="KG">Kg</option>
                    <option value="PACKETS">Packets</option>
                    <option value="ITEMS">Items</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                  Description
                </label>
                <textarea
                  rows={3}
                  value={editForm.description}
                  onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setEditingDonation(null)}
                  className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 font-semibold hover:bg-slate-50 text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={editSaving}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-lg shadow-sm text-xs transition disabled:opacity-50"
                >
                  {editSaving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
