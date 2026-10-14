import React from 'react';
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useAuth } from '../context/AuthContext.jsx';

const navigation = [
  { to: '/dashboard', label: 'Dashboard', icon: '⌂' },
  { to: '/challenges', label: 'Challenges', icon: '◈' },
  { to: '/matching', label: 'AI Matching', icon: '✦', roles: ['student', 'problem_owner', 'mentor', 'faculty', 'admin'] },
  { to: '/teams', label: 'My Teams', icon: '♧', roles: ['student', 'faculty', 'admin'] },
  { to: '/workspace', label: 'Collaboration', icon: '▣', roles: ['student', 'mentor', 'faculty', 'admin'] },
  { to: '/impact', label: 'Review & Impact', icon: '◉' },
  { to: '/profile', label: 'My Profile', icon: '●' },
  { to: '/owner', label: 'Post Challenge', icon: '＋', roles: ['problem_owner', 'admin'] },
];

const roleLabels = {
  student: 'Student',
  problem_owner: 'Problem Owner',
  mentor: 'Industry Mentor',
  faculty: 'University / Faculty',
  admin: 'Admin',
};

const pageTitles = {
  '/dashboard': 'Student Dashboard',
  '/challenges': 'Challenge Hub',
  '/matching': 'AI Matching Engine',
  '/teams': 'My Teams',
  '/workspace': 'Collaboration Workspace',
  '/impact': 'Review & Impact',
  '/profile': 'My Profile',
  '/owner': 'Post a Challenge',
};

export default function AppLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [loggingOut, setLoggingOut] = useState(false);
  const title = location.pathname === '/dashboard'
    ? `${roleLabels[user.role] ?? 'User'} Dashboard`
    : pageTitles[location.pathname] ?? 'Solve Sphere';
  const visibleNavigation = navigation.filter((item) => !item.roles || item.roles.includes(user.role));
  const displayName = user.name || user.email;
  const initials = displayName.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase();

  async function handleLogout() {
    setLoggingOut(true);
    const result = await logout();
    navigate('/login', {
      replace: true,
      state: { notice: result.revoked ? 'You have signed out.' : 'Signed out on this device; the server could not confirm token revocation.' },
    });
    setLoggingOut(false);
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <NavLink className="brand" to="/dashboard" aria-label="Solve Sphere dashboard">
          <span className="brandmark" aria-hidden="true">◎</span>
          <span>Solve Sphere</span>
        </NavLink>
        <nav className="nav" aria-label="Main navigation">
          {visibleNavigation.map((item) => (
            <NavLink
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
              key={item.to}
              to={item.to}
            >
              <span className="nav-icon" aria-hidden="true">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="role"><span className="role-label">Signed in as</span><strong>{roleLabels[user.role] ?? user.role}</strong></div>
      </aside>

      <main className="main">
        <header className="topbar">
          <h1 className="title">{title}</h1>
          <div className="user">
            <span className="user-name">{displayName}</span>
            <span className="avatar" aria-label={`${displayName} profile`}>{initials}</span>
            <button className="btn outline logout-button" disabled={loggingOut} onClick={handleLogout} type="button">
              {loggingOut ? 'Signing out…' : 'Log out'}
            </button>
          </div>
        </header>
        <div className="content">
          <Outlet />
          <footer className="footer-note">Smart India Hackathon 2026 · SIH26043 · DATA FORCE · Solve Sphere</footer>
        </div>
      </main>
    </div>
  );
}