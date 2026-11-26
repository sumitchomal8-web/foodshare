import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ToastProvider } from './context/ToastContext';
import Navbar from './components/Navbar';
import ProtectedRoute from './components/ProtectedRoute';

// Pages
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';

// Donor Pages
import DonorDashboard from './pages/donor/DonorDashboard';
import CreateDonation from './pages/donor/CreateDonation';

// NGO Pages
import NgoBrowse from './pages/ngo/NgoBrowse';
import NgoDeliveries from './pages/ngo/NgoDeliveries';

// Admin Pages
import AdminDashboard from './pages/admin/AdminDashboard';
import AdminNgos from './pages/admin/AdminNgos';
import AdminUsers from './pages/admin/AdminUsers';
import AdminDonations from './pages/admin/AdminDonations';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ToastProvider>
          <div className="min-h-screen flex flex-col bg-slate-50 text-slate-800">
            <Navbar />
            <main className="flex-1 pb-16">
              <Routes>
                {/* Public Routes */}
                <Route path="/" element={<Home />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />

                {/* Donor Routes */}
                <Route element={<ProtectedRoute allowedRoles={['DONOR']} />}>
                  <Route path="/donor" element={<DonorDashboard />} />
                  <Route path="/donor/create" element={<CreateDonation />} />
                </Route>

                {/* NGO Routes */}
                <Route element={<ProtectedRoute allowedRoles={['NGO']} />}>
                  <Route path="/ngo" element={<NgoBrowse />} />
                  <Route path="/ngo/deliveries" element={<NgoDeliveries />} />
                </Route>

                {/* Admin Routes */}
                <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
                  <Route path="/admin" element={<AdminDashboard />} />
                  <Route path="/admin/ngos" element={<AdminNgos />} />
                  <Route path="/admin/users" element={<AdminUsers />} />
                  <Route path="/admin/donations" element={<AdminDonations />} />
                </Route>

                {/* Fallback */}
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </main>
          </div>
        </ToastProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
