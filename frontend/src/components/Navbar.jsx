import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Utensils, HeartHandshake, ShieldCheck, LogOut, User, PlusCircle } from 'lucide-react';

export default function Navbar() {
  const { user, logout, isVerifiedNgo } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-8">
            <Link to="/" className="flex items-center space-x-2 text-emerald-600 font-bold text-xl">
              <Utensils className="h-6 w-6" />
              <span>FoodShare</span>
            </Link>

            {/* Role Navigation */}
            {user && (
              <div className="hidden md:flex items-center space-x-4">
                {user.role === 'DONOR' && (
                  <>
                    <Link
                      to="/donor"
                      className="text-slate-600 hover:text-emerald-600 px-3 py-2 text-sm font-medium"
                    >
                      My Dashboard
                    </Link>
                    <Link
                      to="/donor/create"
                      className="inline-flex items-center text-emerald-600 hover:text-emerald-700 px-3 py-2 text-sm font-medium"
                    >
                      <PlusCircle className="w-4 h-4 mr-1" />
                      Post Donation
                    </Link>
                  </>
                )}

                {user.role === 'NGO' && (
                  <>
                    <Link
                      to="/ngo"
                      className="text-slate-600 hover:text-emerald-600 px-3 py-2 text-sm font-medium"
                    >
                      Browse Available
                    </Link>
                    <Link
                      to="/ngo/deliveries"
                      className="text-slate-600 hover:text-emerald-600 px-3 py-2 text-sm font-medium"
                    >
                      My Deliveries
                    </Link>
                  </>
                )}

                {user.role === 'ADMIN' && (
                  <>
                    <Link
                      to="/admin"
                      className="text-slate-600 hover:text-emerald-600 px-3 py-2 text-sm font-medium"
                    >
                      Overview
                    </Link>
                    <Link
                      to="/admin/ngos"
                      className="text-slate-600 hover:text-emerald-600 px-3 py-2 text-sm font-medium"
                    >
                      Verify NGOs
                    </Link>
                    <Link
                      to="/admin/users"
                      className="text-slate-600 hover:text-emerald-600 px-3 py-2 text-sm font-medium"
                    >
                      Users
                    </Link>
                    <Link
                      to="/admin/donations"
                      className="text-slate-600 hover:text-emerald-600 px-3 py-2 text-sm font-medium"
                    >
                      All Donations
                    </Link>
                  </>
                )}
              </div>
            )}
          </div>

          {/* User profile & actions */}
          <div className="flex items-center space-x-4">
            {user ? (
              <div className="flex items-center space-x-4">
                <div className="flex items-center space-x-2 text-sm">
                  <span className="font-medium text-slate-700">{user.name}</span>
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${
                      user.role === 'ADMIN'
                        ? 'bg-purple-100 text-purple-700'
                        : user.role === 'NGO'
                        ? isVerifiedNgo
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-amber-100 text-amber-700'
                        : 'bg-blue-100 text-blue-700'
                    }`}
                  >
                    {user.role} {user.role === 'NGO' && (isVerifiedNgo ? '✓' : '⌛')}
                  </span>
                </div>
                <button
                  onClick={handleLogout}
                  className="inline-flex items-center text-slate-500 hover:text-rose-600 text-sm font-medium p-1.5 rounded"
                  title="Sign out"
                >
                  <LogOut className="w-5 h-5" />
                </button>
              </div>
            ) : (
              <div className="flex items-center space-x-3">
                <Link
                  to="/login"
                  className="text-slate-600 hover:text-emerald-600 px-3 py-2 text-sm font-medium"
                >
                  Sign In
                </Link>
                <Link
                  to="/register"
                  className="bg-emerald-600 hover:bg-emerald-700 text-white px-4 py-2 rounded-lg text-sm font-medium shadow-sm"
                >
                  Register
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
