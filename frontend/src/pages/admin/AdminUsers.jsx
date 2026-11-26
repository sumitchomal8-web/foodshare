import React, { useState, useEffect } from 'react';
import { api } from '../../api/client';
import { useToast } from '../../context/ToastContext';
import { Users, AlertCircle, CheckCircle2, XCircle } from 'lucide-react';

export default function AdminUsers() {
  const { showToast } = useToast();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [roleFilter, setRoleFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState('');
  const [actionLoading, setActionLoading] = useState(null);
  const [error, setError] = useState('');

  const fetchUsers = async () => {
    setLoading(true);
    setError('');
    try {
      const params = {};
      if (roleFilter) params.role = roleFilter;
      if (activeFilter !== '') params.is_active = activeFilter === 'true';

      const res = await api.admin.getUsers(params);
      setUsers(res.items || []);
    } catch (err) {
      setError(err.detail || 'Failed to fetch users');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [roleFilter, activeFilter]);

  const handleToggleStatus = async (id, currentStatus) => {
    const newStatus = !currentStatus;
    const actionLabel = newStatus ? 'Activate' : 'Deactivate';
    if (!window.confirm(`${actionLabel} this user account?`)) return;

    setActionLoading(id);
    try {
      await api.admin.setUserStatus(id, newStatus);
      showToast(`User account ${newStatus ? 'activated' : 'deactivated'} successfully`, 'info');
      await fetchUsers();
    } catch (err) {
      showToast(err.detail || `Failed to ${actionLabel.toLowerCase()} user`, 'error');
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">User Management</h1>
          <p className="text-sm text-slate-500 mt-1">Inspect accounts, filter roles, and toggle access permissions</p>
        </div>

        {/* Filters */}
        <div className="flex gap-3">
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-semibold"
          >
            <option value="">All Roles</option>
            <option value="DONOR">Donors</option>
            <option value="NGO">NGOs</option>
            <option value="ADMIN">Admins</option>
          </select>

          <select
            value={activeFilter}
            onChange={(e) => setActiveFilter(e.target.value)}
            className="px-3 py-1.5 bg-white border border-slate-300 rounded-lg text-xs font-semibold"
          >
            <option value="">All Statuses</option>
            <option value="true">Active</option>
            <option value="false">Disabled</option>
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
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-slate-500 font-semibold text-xs uppercase text-left">
              <tr>
                <th className="px-6 py-3">Name / Email</th>
                <th className="px-6 py-3">Role</th>
                <th className="px-6 py-3">City / Phone</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-slate-50/50">
                  <td className="px-6 py-4">
                    <div className="font-bold text-slate-900">{u.name}</div>
                    <div className="text-xs text-slate-500">{u.email}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded text-xs font-semibold ${
                        u.role === 'ADMIN'
                          ? 'bg-purple-100 text-purple-700'
                          : u.role === 'NGO'
                          ? 'bg-blue-100 text-blue-700'
                          : 'bg-emerald-100 text-emerald-700'
                      }`}
                    >
                      {u.role}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-xs text-slate-600">
                    <div>{u.address?.city || 'N/A'}</div>
                    <div className="text-slate-400">{u.phone}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${
                        u.is_active
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-rose-100 text-rose-800'
                      }`}
                    >
                      {u.is_active ? 'Active' : 'Disabled'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => handleToggleStatus(u.id, u.is_active)}
                      disabled={actionLoading === u.id}
                      className={`text-xs font-semibold px-3 py-1 rounded transition ${
                        u.is_active
                          ? 'text-rose-600 hover:bg-rose-50 border border-rose-200'
                          : 'text-emerald-600 hover:bg-emerald-50 border border-emerald-200'
                      }`}
                    >
                      {actionLoading === u.id
                        ? 'Updating...'
                        : u.is_active
                        ? 'Deactivate'
                        : 'Activate'}
                    </button>
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
