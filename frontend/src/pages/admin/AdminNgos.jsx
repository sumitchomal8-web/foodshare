import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import StatusBadge from '../../components/StatusBadge';
import { useToast } from '../../context/ToastContext';
import { Check, X, Shield, AlertCircle, Building2, MapPin, Phone, Mail } from 'lucide-react';

export default function AdminNgos() {
  const { showToast } = useToast();
  const [ngos, setNgos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(null);

  const fetchPendingNgos = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.admin.getPendingNgos();
      setNgos(res.items || []);
    } catch (err) {
      setError(err.detail || 'Failed to fetch pending NGOs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPendingNgos();
  }, []);

  const handleVerify = async (id, approve) => {
    const actionLabel = approve ? 'Approve' : 'Reject';
    if (!window.confirm(`${actionLabel} verification for this organization?`)) return;

    setActionLoading(id);
    try {
      await api.admin.verifyNgo(id, approve);
      showToast(`NGO application ${approve ? 'approved' : 'rejected'} successfully`, approve ? 'success' : 'info');
      await fetchPendingNgos();
    } catch (err) {
      showToast(err.detail || `Failed to ${actionLabel.toLowerCase()} NGO`, 'error');
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-6">
      <div className="border-b border-slate-200 pb-5">
        <h1 className="text-2xl font-bold text-slate-900">NGO Verification Requests</h1>
        <p className="text-sm text-slate-500 mt-1">
          Review credentials and grant verified status to genuine food rescue partners
        </p>
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
      ) : ngos.length === 0 ? (
        <div className="text-center py-16 bg-white rounded-2xl border border-slate-200 p-8">
          <Shield className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
          <p className="text-slate-700 font-bold text-base">All Caught Up!</p>
          <p className="text-slate-400 text-xs mt-1">There are no pending NGO verification applications.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {ngos.map((ngo) => (
            <div
              key={ngo.id}
              className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4"
            >
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <h3 className="font-bold text-slate-900 text-lg">
                    {ngo.ngo_profile?.organization_name || ngo.name}
                  </h3>
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                    {ngo.ngo_profile?.org_type || 'NGO'}
                  </span>
                  <StatusBadge status={ngo.ngo_profile?.verification_status || 'PENDING'} />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-1 text-xs text-slate-600">
                  <div className="flex items-center gap-1.5">
                    <Building2 className="w-3.5 h-3.5 text-slate-400" />
                    <span>Reg: {ngo.ngo_profile?.registration_number || 'N/A'}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 text-slate-400" />
                    <span>{ngo.email}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Phone className="w-3.5 h-3.5 text-slate-400" />
                    <span>{ngo.phone}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-slate-400" />
                    <span>
                      {ngo.address?.city}, {ngo.address?.state}
                    </span>
                  </div>
                </div>
              </div>

              {/* Approve / Reject Actions */}
              <div className="flex items-center gap-2 w-full md:w-auto">
                <button
                  onClick={() => handleVerify(ngo.id, true)}
                  disabled={actionLoading === ngo.id}
                  className="flex-1 md:flex-none inline-flex items-center justify-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-4 py-2 rounded-lg text-xs shadow-sm transition"
                >
                  <Check className="w-4 h-4" />
                  <span>Approve</span>
                </button>
                <button
                  onClick={() => handleVerify(ngo.id, false)}
                  disabled={actionLoading === ngo.id}
                  className="flex-1 md:flex-none inline-flex items-center justify-center gap-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 font-semibold px-4 py-2 rounded-lg text-xs border border-rose-200 transition"
                >
                  <X className="w-4 h-4" />
                  <span>Reject</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
