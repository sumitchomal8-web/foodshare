import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../api/client';
import { Users, Utensils, HeartHandshake, ShieldCheck, CheckCircle2, AlertTriangle, ArrowRight } from 'lucide-react';

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function loadStats() {
      try {
        const data = await api.admin.getStats();
        setStats(data);
      } catch (err) {
        setError(err.detail || 'Failed to load platform statistics');
      } finally {
        setLoading(false);
      }
    }
    loadStats();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center py-24">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto py-8 px-4 text-rose-600 bg-rose-50 p-4 rounded-xl">
        {error}
      </div>
    );
  }

  const { users, donations } = stats || {};

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Platform Overview & Analytics</h1>
        <p className="text-sm text-slate-500 mt-1">Real-time metrics on food donations, verification, and community impact</p>
      </div>

      {/* Pending NGO Alert Card if any pending */}
      {users?.pending_ngos > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-amber-100 rounded-xl text-amber-700">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-amber-900">
                {users.pending_ngos} NGO{users.pending_ngos > 1 ? 's' : ''} Awaiting Verification
              </h3>
              <p className="text-xs text-amber-700 mt-0.5">
                Review and approve organizations so they can start collecting surplus food.
              </p>
            </div>
          </div>
          <Link
            to="/admin/ngos"
            className="inline-flex items-center gap-1.5 bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-sm"
          >
            <span>Review Applications</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      )}

      {/* Primary Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Total Donations</span>
            <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg">
              <Utensils className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-slate-900">{donations?.total || 0}</p>
          <p className="text-xs text-slate-400 mt-1">{donations?.completed || 0} completed successfully</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Active Listings</span>
            <div className="p-2 bg-blue-50 text-blue-600 rounded-lg">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-slate-900">{donations?.active || 0}</p>
          <p className="text-xs text-slate-400 mt-1">Available or in transit</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Verified NGOs</span>
            <div className="p-2 bg-purple-50 text-purple-600 rounded-lg">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-slate-900">{users?.verified_ngos || 0}</p>
          <p className="text-xs text-slate-400 mt-1">Active collection partners</p>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
          <div className="flex justify-between items-start mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Registered Donors</span>
            <div className="p-2 bg-amber-50 text-amber-600 rounded-lg">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <p className="text-3xl font-extrabold text-slate-900">{users?.donors || 0}</p>
          <p className="text-xs text-slate-400 mt-1">Businesses & individuals</p>
        </div>
      </div>

      {/* Breakdown by Food Type */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
        <h2 className="text-base font-bold text-slate-900 mb-4">Donations by Food Type</h2>
        {donations?.by_food_type && Object.keys(donations.by_food_type).length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
            {Object.entries(donations.by_food_type).map(([type, count]) => (
              <div key={type} className="bg-slate-50 p-4 rounded-xl text-center border border-slate-100">
                <span className="text-xs font-bold uppercase text-slate-500">{type}</span>
                <p className="text-2xl font-bold text-slate-900 mt-1">{count}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-400">No donations recorded yet.</p>
        )}
      </div>

      {/* Quick Action Navigation */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Link
          to="/admin/ngos"
          className="p-5 bg-white rounded-xl border border-slate-200 hover:border-emerald-500 hover:shadow transition group"
        >
          <h3 className="font-bold text-slate-900 group-hover:text-emerald-600 flex items-center justify-between">
            <span>NGO Verifications</span>
            <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-emerald-600" />
          </h3>
          <p className="text-xs text-slate-500 mt-1">Review pending applications and verify registrations</p>
        </Link>

        <Link
          to="/admin/users"
          className="p-5 bg-white rounded-xl border border-slate-200 hover:border-emerald-500 hover:shadow transition group"
        >
          <h3 className="font-bold text-slate-900 group-hover:text-emerald-600 flex items-center justify-between">
            <span>User Management</span>
            <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-emerald-600" />
          </h3>
          <p className="text-xs text-slate-500 mt-1">View all platform users, roles, and toggle account activation</p>
        </Link>

        <Link
          to="/admin/donations"
          className="p-5 bg-white rounded-xl border border-slate-200 hover:border-emerald-500 hover:shadow transition group"
        >
          <h3 className="font-bold text-slate-900 group-hover:text-emerald-600 flex items-center justify-between">
            <span>All Platform Donations</span>
            <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-emerald-600" />
          </h3>
          <p className="text-xs text-slate-500 mt-1">Audit complete donation histories and lifecycle states</p>
        </Link>
      </div>
    </div>
  );
}
