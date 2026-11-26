import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Heart, Utensils, ShieldCheck, Truck, Users } from 'lucide-react';

export default function Home() {
  const { user } = useAuth();

  return (
    <div className="space-y-16 py-8">
      {/* Hero Section */}
      <section className="text-center max-w-4xl mx-auto px-4">
        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 mb-4">
          Rescuing Surplus Food • Feeding Communities
        </span>
        <h1 className="text-4xl sm:text-5xl font-extrabold text-slate-900 tracking-tight leading-tight">
          Bridge the Gap Between <span className="text-emerald-600">Surplus Food</span> and{' '}
          <span className="text-emerald-600">Hunger</span>
        </h1>
        <p className="mt-4 text-lg text-slate-600 max-w-2xl mx-auto">
          FoodShare coordinates immediate food rescue by linking verified NGOs, volunteers, and surplus donors through a trusted, transparent platform.
        </p>
        <div className="mt-8 flex justify-center gap-4">
          {user ? (
            <Link
              to={user.role === 'DONOR' ? '/donor' : user.role === 'NGO' ? '/ngo' : '/admin'}
              className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-6 py-3 rounded-lg shadow"
            >
              Go to Dashboard
            </Link>
          ) : (
            <>
              <Link
                to="/register"
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold px-6 py-3 rounded-lg shadow"
              >
                Join FoodShare
              </Link>
              <Link
                to="/login"
                className="bg-white hover:bg-slate-50 text-slate-700 font-semibold px-6 py-3 rounded-lg border border-slate-300 shadow-sm"
              >
                Sign In
              </Link>
            </>
          )}
        </div>
      </section>

      {/* Feature Pillars */}
      <section className="max-w-7xl mx-auto px-4 grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition">
          <div className="w-12 h-12 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center mb-4">
            <Utensils className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-bold text-slate-900 mb-2">Food Donors</h3>
          <p className="text-slate-600 text-sm leading-relaxed">
            Restaurants, caterers, and individuals list surplus food with pickup location, quantities, and expiration times in seconds.
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition">
          <div className="w-12 h-12 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center mb-4">
            <Truck className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-bold text-slate-900 mb-2">Verified NGOs</h3>
          <p className="text-slate-600 text-sm leading-relaxed">
            Vetted non-profit organizations claim food donations, pick them up safely, and distribute them to families in need.
          </p>
        </div>

        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition">
          <div className="w-12 h-12 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center mb-4">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-bold text-slate-900 mb-2">Platform Oversight</h3>
          <p className="text-slate-600 text-sm leading-relaxed">
            Strict admin verification ensures only genuine organizations participate, while real-time metrics track impact.
          </p>
        </div>
      </section>
    </div>
  );
}
