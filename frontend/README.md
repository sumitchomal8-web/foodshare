# FoodShare – Frontend Application

Modern single-page application for the FoodShare surplus food rescue platform, built with **React**, **Vite**, and **Tailwind CSS**.

---

## 1. Tech Stack

- **Framework:** React 18
- **Tooling & Bundler:** Vite 5
- **Routing:** React Router DOM v6
- **Styling:** Tailwind CSS v3
- **Icons:** Lucide React
- **API Communication:** Native Fetch client with JWT Bearer authentication and development reverse proxy (`/api/v1` -> `http://127.0.0.1:8000`)

---

## 2. Directory Structure

```
frontend/
├── package.json
├── vite.config.js          # Configures port 3000 and reverse proxy to FastAPI
├── tailwind.config.js      # Custom theme colors (brand-50 to brand-700)
├── postcss.config.js
├── index.html
└── src/
    ├── main.jsx            # React root mount
    ├── App.jsx             # Route definitions & layout structure
    ├── index.css           # Tailwind base, components, and utilities
    ├── api/
    │   └── client.js       # Typed API client matching Master Spec endpoints
    ├── context/
    │   └── AuthContext.jsx # Global auth state, JWT storage, role verification
    ├── components/
    │   ├── Navbar.jsx      # Role-aware top navigation bar
    │   ├── ProtectedRoute.jsx # Role-based access control route wrapper
    │   └── StatusBadge.jsx # Universal status pill for donations & verification
    └── pages/
        ├── Home.jsx        # Landing page with mission pillars
        ├── Login.jsx       # Email & password authentication
        ├── Register.jsx    # Dual-role registration (Donor vs NGO/Volunteer)
        ├── donor/
        │   ├── DonorDashboard.jsx # Donor's active & past donations, cancel action
        │   └── CreateDonation.jsx # Surplus food post form with location pre-fill
        ├── ngo/
        │   ├── NgoBrowse.jsx      # Available donations grid, city & food type filters, claim action
        │   └── NgoDeliveries.jsx  # Accepted donations, lifecycle state buttons (Pick Up -> Distribute -> Complete)
        └── admin/
            ├── AdminDashboard.jsx # Platform KPI analytics, food type breakdown, quick actions
            ├── AdminNgos.jsx      # Pending NGO verification review & one-click approve/reject
            ├── AdminUsers.jsx     # User registry, role filtering, active/disable toggle
            └── AdminDonations.jsx # Platform-wide donation audit table
```

---

## 3. Getting Started

### Development Server
From the `frontend/` directory:

```powershell
npm run dev
```

The app will run at `http://localhost:3000` and automatically forward `/api` requests to the FastAPI backend running on port 8000.

### Production Build
```powershell
npm run build
```

Build outputs are saved to `frontend/dist/`.
