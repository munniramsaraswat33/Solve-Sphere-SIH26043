import React from 'react';
import { Link, Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';

export default function ProtectedRoute({ allowedRoles }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <main aria-live="polite" className="auth-loading">Checking your session…</main>;
  }
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return (
      <section className="access-denied">
        <div className="auth-card">
          <span className="auth-kicker">Solve Sphere</span>
          <h1>Access denied</h1>
          <p className="muted">Your account role does not have access to this page.</p>
          <Link className="btn primary" to="/dashboard">Return to dashboard</Link>
        </div>
      </section>
    );
  }
  return <Outlet />;
}