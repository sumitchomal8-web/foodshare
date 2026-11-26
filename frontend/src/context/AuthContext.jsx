import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('foodshare_token'));
  const [loading, setLoading] = useState(true);

  // Load user profile on token change
  useEffect(() => {
    async function loadUser() {
      if (!token) {
        setUser(null);
        setLoading(false);
        return;
      }
      try {
        const profile = await api.users.getMe();
        setUser(profile);
      } catch (err) {
        console.error('Failed to load user profile', err);
        localStorage.removeItem('foodshare_token');
        setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    }
    loadUser();
  }, [token]);

  const login = async (email, password) => {
    const res = await api.auth.login({ email, password });
    localStorage.setItem('foodshare_token', res.access_token);
    setToken(res.access_token);
    const profile = await api.users.getMe();
    setUser(profile);
    return profile;
  };

  const register = async (payload) => {
    await api.auth.register(payload);
    // Automatically log in after registration
    return await login(payload.email, payload.password);
  };

  const logout = () => {
    localStorage.removeItem('foodshare_token');
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    if (token) {
      const profile = await api.users.getMe();
      setUser(profile);
    }
  };

  const isVerifiedNgo =
    user?.role === 'NGO' && user?.ngo_profile?.verification_status === 'VERIFIED';

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        register,
        logout,
        refreshUser,
        isVerifiedNgo,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
