/**
 * FoodShare API Client
 * Wraps all REST endpoints conforming to the Master Specification
 */

const API_BASE = '/api/v1';

async function request(endpoint, options = {}) {
  const token = localStorage.getItem('foodshare_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  const isJson = response.headers.get('content-type')?.includes('application/json');
  const data = isJson ? await response.json() : null;

  if (!response.ok) {
    const error = new Error(data?.detail || 'Request failed');
    error.status = response.status;
    error.code = data?.code || 'ERROR';
    error.detail = data?.detail || 'An unknown error occurred';
    throw error;
  }

  return data;
}

export const api = {
  // Auth endpoints
  auth: {
    login: (credentials) =>
      request('/auth/login', {
        method: 'POST',
        body: JSON.stringify(credentials),
      }),
    register: (payload) =>
      request('/auth/register', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
  },

  // User profile
  users: {
    getMe: () => request('/users/me'),
    updateMe: (payload) =>
      request('/users/me', {
        method: 'PUT',
        body: JSON.stringify(payload),
      }),
  },

  // Donor endpoints
  donor: {
    createDonation: (payload) =>
      request('/donations', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
    getMyDonations: (params = {}) => {
      const q = new URLSearchParams(params).toString();
      return request(`/donations/mine${q ? `?${q}` : ''}`);
    },
    updateDonation: (id, payload) =>
      request(`/donations/${id}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      }),
    cancelDonation: (id) =>
      request(`/donations/${id}/cancel`, {
        method: 'POST',
      }),
  },

  // NGO & Shared Donation endpoints
  donations: {
    browse: (params = {}) => {
      const q = new URLSearchParams(params).toString();
      return request(`/donations${q ? `?${q}` : ''}`);
    },
    getDetail: (id) => request(`/donations/${id}`),
    accept: (id) =>
      request(`/donations/${id}/accept`, {
        method: 'POST',
      }),
    pickup: (id) =>
      request(`/donations/${id}/pickup`, {
        method: 'POST',
      }),
    distribute: (id) =>
      request(`/donations/${id}/distribute`, {
        method: 'POST',
      }),
    complete: (id) =>
      request(`/donations/${id}/complete`, {
        method: 'POST',
      }),
  },

  // NGO specific
  ngo: {
    getMyDonations: (params = {}) => {
      const q = new URLSearchParams(params).toString();
      return request(`/ngo/donations${q ? `?${q}` : ''}`);
    },
  },

  // Admin endpoints
  admin: {
    getStats: () => request('/admin/stats'),
    getUsers: (params = {}) => {
      const q = new URLSearchParams(params).toString();
      return request(`/admin/users${q ? `?${q}` : ''}`);
    },
    setUserStatus: (id, isActive) =>
      request(`/admin/users/${id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: isActive }),
      }),
    getPendingNgos: (params = {}) => {
      const q = new URLSearchParams(params).toString();
      return request(`/admin/ngos/pending${q ? `?${q}` : ''}`);
    },
    verifyNgo: (id, approve) =>
      request(`/admin/ngos/${id}/verify`, {
        method: 'POST',
        body: JSON.stringify({ approve }),
      }),
    getDonations: (params = {}) => {
      const q = new URLSearchParams(params).toString();
      return request(`/admin/donations${q ? `?${q}` : ''}`);
    },
  },
};
