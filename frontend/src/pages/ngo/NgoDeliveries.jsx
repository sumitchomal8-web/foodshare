import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import StatusBadge from '../../components/StatusBadge';
import ImageUploadField from '../../components/ImageUploadField';
import { useToast } from '../../context/ToastContext';
import { Truck, CheckCircle2, Clock, MapPin, Package, ArrowRight, AlertCircle } from 'lucide-react';

export default function NgoDeliveries() {
  const { showToast } = useToast();
  const [donations, setDonations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [actionLoading, setActionLoading] = useState(null);
  const [proofImages, setProofImages] = useState({});
  const [error, setError] = useState('');

  const fetchMyDeliveries = async () => {
    setLoading(true);
    setError('');
    try {
      const params = {};
      if (statusFilter) params.status = statusFilter;
      const res = await api.ngo.getMyDonations(params);
      setDonations(res.items || []);
    } catch (err) {
      setError(err.detail || 'Failed to fetch deliveries');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMyDeliveries();
  }, [statusFilter]);

  const handleTransition = async (id, action) => {
    const proofUrl = proofImages[id] || '';
    if ((action === 'pickup' || action === 'distribute') && !proofUrl) {
      showToast(
        action === 'pickup'
          ? 'Please upload a pickup proof photo first.'
          : 'Please upload a delivery/drop proof photo first.',
        'error'
      );
      return;
    }

    setActionLoading(id);
    try {
      if (action === 'pickup') {
        await api.donations.pickup(id, proofUrl);
        showToast('Donation marked as Picked Up!', 'success');
      } else if (action === 'distribute') {
        await api.donations.distribute(id, proofUrl);
        showToast('Donation marked as Distributed!', 'success');
      } else if (action === 'complete') {
        await api.donations.complete(id, proofUrl || undefined);
        showToast('Donation marked as Completed!', 'success');
      }

      setProofImages((prev) => {
        const next = { ...prev };
        delete next[id];
        return next;
      });
      await fetchMyDeliveries();
    } catch (err) {
      showToast(err.detail || `Failed to transition donation: ${err.message}`, 'error');
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">My Deliveries & Pickups</h1>
          <p className="text-sm text-slate-500 mt-1">
            Track and update the status of donations accepted by your organization
          </p>
        </div>

        {/* Status Tab Filters */}
        <div className="flex flex-wrap gap-1 bg-slate-100 p-1 rounded-lg text-xs font-semibold">
          {['', 'ACCEPTED', 'PICKED_UP', 'DISTRIBUTED', 'COMPLETED'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-md transition ${
                statusFilter === st
                  ? 'bg-white text-emerald-700 shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {st === '' ? 'All' : st.replace('_', ' ')}
            </button>
          ))}
        </div>
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
          <Truck className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-600 font-medium text-base">No accepted deliveries found.</p>
          <p className="text-slate-400 text-xs mt-1">Browse available food donations to claim items.</p>
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
                    <span className="font-semibold text-slate-800">
                      {d.quantity} {d.quantity_unit}
                    </span>
                    <span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded uppercase font-semibold">
                      {d.food_type}
                    </span>
                  </div>

                  <div className="flex items-start gap-1.5 text-xs text-slate-500 pt-1">
                    <MapPin className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" />
                    <span>
                      {d.pickup_address?.street}, {d.pickup_address?.city}
                    </span>
                  </div>

                  {/* Proof Photos */}
                  {(d.food_image_url || d.pickup_image_url || d.delivery_image_url) && (
                    <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-100">
                      {d.food_image_url && (
                        <a href={d.food_image_url} target="_blank" rel="noopener noreferrer" className="text-center">
                          <img src={d.food_image_url} alt="Donor food" className="h-14 w-14 rounded-lg object-cover border border-slate-200" />
                          <span className="block text-[10px] text-slate-500 mt-0.5">Food</span>
                        </a>
                      )}
                      {d.pickup_image_url && (
                        <a href={d.pickup_image_url} target="_blank" rel="noopener noreferrer" className="text-center">
                          <img src={d.pickup_image_url} alt="Pickup proof" className="h-14 w-14 rounded-lg object-cover border border-slate-200" />
                          <span className="block text-[10px] text-slate-500 mt-0.5">Pickup</span>
                        </a>
                      )}
                      {d.delivery_image_url && (
                        <a href={d.delivery_image_url} target="_blank" rel="noopener noreferrer" className="text-center">
                          <img src={d.delivery_image_url} alt="Delivery proof" className="h-14 w-14 rounded-lg object-cover border border-slate-200" />
                          <span className="block text-[10px] text-slate-500 mt-0.5">Drop</span>
                        </a>
                      )}
                    </div>
                  )}

                  {/* Timeline timestamps */}
                  <div className="text-xs text-slate-400 border-t border-slate-100 pt-2 space-y-1">
                    {d.accepted_at && (
                      <p>Accepted: {new Date(d.accepted_at).toLocaleString()}</p>
                    )}
                    {d.picked_up_at && (
                      <p>Picked up: {new Date(d.picked_up_at).toLocaleString()}</p>
                    )}
                    {d.distributed_at && (
                      <p>Distributed: {new Date(d.distributed_at).toLocaleString()}</p>
                    )}
                    {d.completed_at && (
                      <p>Completed: {new Date(d.completed_at).toLocaleString()}</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Status Transition Action Buttons */}
              <div className="border-t border-slate-100 pt-3 space-y-3">
                {d.status === 'ACCEPTED' && (
                  <>
                    <ImageUploadField
                      label="Pickup Proof Photo"
                      required
                      compact
                      value={proofImages[d.id] || ''}
                      onChange={(url) =>
                        setProofImages((prev) => ({ ...prev, [d.id]: url }))
                      }
                    />
                    <button
                      onClick={() => handleTransition(d.id, 'pickup')}
                      disabled={actionLoading === d.id || !proofImages[d.id]}
                      className="w-full flex items-center justify-center gap-2 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white font-semibold py-2 px-4 rounded-lg text-sm shadow-sm transition"
                    >
                      <Truck className="w-4 h-4" />
                      <span>{actionLoading === d.id ? 'Updating...' : 'Mark as Picked Up'}</span>
                    </button>
                  </>
                )}

                {d.status === 'PICKED_UP' && (
                  <>
                    <ImageUploadField
                      label="Drop / Delivery Proof Photo"
                      required
                      compact
                      value={proofImages[d.id] || ''}
                      onChange={(url) =>
                        setProofImages((prev) => ({ ...prev, [d.id]: url }))
                      }
                    />
                    <button
                      onClick={() => handleTransition(d.id, 'distribute')}
                      disabled={actionLoading === d.id || !proofImages[d.id]}
                      className="w-full flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white font-semibold py-2 px-4 rounded-lg text-sm shadow-sm transition"
                    >
                      <Package className="w-4 h-4" />
                      <span>{actionLoading === d.id ? 'Updating...' : 'Mark as Distributed'}</span>
                    </button>
                  </>
                )}

                {d.status === 'DISTRIBUTED' && (
                  <button
                    onClick={() => handleTransition(d.id, 'complete')}
                    disabled={actionLoading === d.id}
                    className="w-full flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-2 px-4 rounded-lg text-sm shadow-sm transition"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    <span>{actionLoading === d.id ? 'Updating...' : 'Mark as Completed'}</span>
                  </button>
                )}

                {d.status === 'COMPLETED' && (
                  <div className="flex items-center justify-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 py-2 rounded-lg">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span>Delivery Completed Successfully</span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
