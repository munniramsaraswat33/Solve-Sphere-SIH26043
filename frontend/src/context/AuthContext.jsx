import React, { createContext, useContext, useEffect, useState } from 'react';
import api from '../services/api.js';

const AuthContext = createContext(null);
const TOKEN_KEY = 'solve-sphere-access-token';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const token = sessionStorage.getItem(TOKEN_KEY);

    if (!token) {
      setLoading(false);
      return () => { active = false; };
    }

    api.get('/api/auth/me')
      .then(({ data }) => { if (active) setUser(data); })
      .catch(() => {
        sessionStorage.removeItem(TOKEN_KEY);
        if (active) setUser(null);
      })
      .finally(() => { if (active) setLoading(false); });

    return () => { active = false; };
  }, []);

  function acceptAuthResponse(data) {
    sessionStorage.setItem(TOKEN_KEY, data.access_token);
    setUser(data.user);
    return data.user;
  }

  async function login(credentials) {
    const { data } = await api.post('/api/auth/login', credentials);
    return acceptAuthResponse(data);
  }

  async function register(role, account) {
    const { data } = await api.post(`/api/auth/register/${role}`, account);
    return acceptAuthResponse(data);
  }

  async function googleLogin(idToken, role = 'student') {
    const { data } = await api.post('/api/auth/google', { id_token: idToken, role });
    return acceptAuthResponse(data);
  }

  async function updateProfile(profile) {
    const { data } = await api.patch('/api/auth/me', profile);
    setUser(data);
    return data;
  }

  async function logout() {
    let revoked = false;
    try {
      await api.post('/api/auth/logout');
      revoked = true;
    } catch {
      revoked = false;
    } finally {
      sessionStorage.removeItem(TOKEN_KEY);
      setUser(null);
    }
    return { revoked };
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, googleLogin, updateProfile, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}