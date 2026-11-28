import React, { useState } from 'react';
import { api } from '../api/client';
import { Camera, X, Loader2 } from 'lucide-react';

const MAX_BYTES = 3 * 1024 * 1024; // 3 MB
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

export default function ImageUploadField({
  label,
  value,
  onChange,
  required = false,
  compact = false,
}) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError('');
    if (!ALLOWED_TYPES.includes(file.type)) {
      setError('Only JPG, PNG, or WEBP images are allowed.');
      e.target.value = '';
      return;
    }

    if (file.size > MAX_BYTES) {
      setError('Image must be 3 MB or smaller.');
      e.target.value = '';
      return;
    }

    setUploading(true);
    try {
      const res = await api.uploads.uploadImage(file);
      onChange(res.url);
    } catch (err) {
      setError(err.detail || 'Failed to upload image.');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  return (
    <div className="space-y-1.5">
      {label && (
        <label className="block text-xs font-semibold text-slate-700 uppercase">
          {label} {required && '*'}
        </label>
      )}

      {value ? (
        <div className="relative inline-block">
          <img
            src={value}
            alt={label || 'Uploaded proof'}
            className={`${compact ? 'h-24 w-36' : 'h-36 w-56'} rounded-lg object-cover border border-slate-200`}
          />
          <button
            type="button"
            onClick={() => onChange('')}
            title="Remove image"
            className="absolute -top-2 -right-2 rounded-full bg-rose-600 p-1 text-white shadow hover:bg-rose-700"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ) : (
        <label className="flex cursor-pointer items-center justify-center gap-2 rounded-lg border border-dashed border-slate-300 bg-slate-50 px-3 py-2.5 text-xs font-medium text-slate-600 hover:border-emerald-500 hover:bg-emerald-50/40 transition">
          {uploading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-emerald-600" />
              <span>Uploading to cloud...</span>
            </>
          ) : (
            <>
              <Camera className="w-4 h-4 text-emerald-600" />
              <span>Upload Photo (JPG/PNG/WEBP, max 3 MB)</span>
            </>
          )}
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={handleFileChange}
            disabled={uploading}
            className="hidden"
          />
        </label>
      )}

      {error && <p className="text-xs text-rose-600 font-medium">{error}</p>}
    </div>
  );
}
