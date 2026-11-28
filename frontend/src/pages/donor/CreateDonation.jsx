import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import ImageUploadField from '../../components/ImageUploadField';
import { Utensils, AlertCircle } from 'lucide-react';

export default function CreateDonation() {
  const { user } = useAuth();
  const navigate = useNavigate();

  // Set default available_from (now) and expires_at (4 hours from now)
  const now = new Date();
  const defaultAvailable = new Date(now.getTime() - now.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
  const defaultExpires = new Date(now.getTime() + 4 * 3600 * 1000 - now.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);

  const [formData, setFormData] = useState({
    title: '',
    food_type: 'COOKED',
    quantity: '',
    quantity_unit: 'PLATES',
    description: '',
    food_image_url: '',
    available_from: defaultAvailable,
    expires_at: defaultExpires,
    street: user?.address?.street || '',
    city: user?.address?.city || '',
    state: user?.address?.state || '',
    pincode: user?.address?.pincode || '',
  });

  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const payload = {
      title: formData.title,
      food_type: formData.food_type,
      quantity: Number(formData.quantity),
      quantity_unit: formData.quantity_unit,
      description: formData.description || null,
      food_image_url: formData.food_image_url || null,
      available_from: new Date(formData.available_from).toISOString(),
      expires_at: new Date(formData.expires_at).toISOString(),
      pickup_address: {
        street: formData.street,
        city: formData.city,
        state: formData.state,
        pincode: formData.pincode,
      },
    };

    try {
      await api.donor.createDonation(payload);
      navigate('/donor');
    } catch (err) {
      setError(err.detail || 'Failed to create donation. Check your inputs.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <div className="bg-white p-8 rounded-2xl border border-slate-200 shadow-sm">
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 rounded-xl bg-emerald-100 text-emerald-600">
            <Utensils className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">List Surplus Food Donation</h1>
            <p className="text-xs text-slate-500">Provide accurate details for collecting NGOs</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-rose-50 border border-rose-200 rounded-lg flex items-center gap-2 text-sm text-rose-700">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
              Donation Title *
            </label>
            <input
              type="text"
              required
              name="title"
              value={formData.title}
              onChange={handleChange}
              placeholder="e.g. Veg Pulao & Curry (40 plates)"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 text-sm"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Food Type *
              </label>
              <select
                name="food_type"
                value={formData.food_type}
                onChange={handleChange}
                className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 text-sm"
              >
                <option value="COOKED">Cooked</option>
                <option value="PACKAGED">Packaged</option>
                <option value="RAW">Raw</option>
                <option value="BAKERY">Bakery</option>
                <option value="OTHER">Other</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Quantity *
              </label>
              <input
                type="number"
                min="0.1"
                step="any"
                required
                name="quantity"
                value={formData.quantity}
                onChange={handleChange}
                placeholder="e.g. 25"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Unit *
              </label>
              <select
                name="quantity_unit"
                value={formData.quantity_unit}
                onChange={handleChange}
                className="w-full px-3 py-2 bg-white border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 text-sm"
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
              Description / Notes (Optional)
            </label>
            <textarea
              name="description"
              rows={2}
              value={formData.description}
              onChange={handleChange}
              placeholder="Freshly prepared for a banquet. Stored in hot cases."
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 text-sm"
            />
          </div>

          <ImageUploadField
            label="Food Photo (Optional, max 3 MB)"
            value={formData.food_image_url}
            onChange={(url) => setFormData((prev) => ({ ...prev, food_image_url: url }))}
          />

          {/* Timing */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Available From *
              </label>
              <input
                type="datetime-local"
                required
                name="available_from"
                value={formData.available_from}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Expires At *
              </label>
              <input
                type="datetime-local"
                required
                name="expires_at"
                value={formData.expires_at}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 text-sm"
              />
            </div>
          </div>

          {/* Pickup Address */}
          <div className="border-t border-slate-100 pt-4">
            <h3 className="text-xs font-bold uppercase text-slate-500 tracking-wider mb-2">
              Pickup Location
            </h3>
            <div className="space-y-3">
              <input
                type="text"
                required
                name="street"
                value={formData.street}
                onChange={handleChange}
                placeholder="Street Address / Gate / Landmark"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 text-sm"
              />
              <div className="grid grid-cols-3 gap-3">
                <input
                  type="text"
                  required
                  name="city"
                  value={formData.city}
                  onChange={handleChange}
                  placeholder="City"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 text-sm"
                />
                <input
                  type="text"
                  required
                  name="state"
                  value={formData.state}
                  onChange={handleChange}
                  placeholder="State"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 text-sm"
                />
                <input
                  type="text"
                  required
                  name="pincode"
                  value={formData.pincode}
                  onChange={handleChange}
                  placeholder="Pincode"
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 text-sm"
                />
              </div>
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={() => navigate('/donor')}
              className="flex-1 py-2.5 border border-slate-300 rounded-lg text-slate-700 font-semibold hover:bg-slate-50 text-sm"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-lg shadow-sm transition disabled:opacity-50 text-sm"
            >
              {loading ? 'Publishing...' : 'Publish Donation'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
