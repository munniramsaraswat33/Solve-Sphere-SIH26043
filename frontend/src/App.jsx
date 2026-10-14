import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import AppLayout from './components/AppLayout.jsx';
import ProtectedRoute from './components/ProtectedRoute.jsx';
import { LoginPage, RegisterPage } from './pages/AuthPages.jsx';
import {
  ChallengeHub,
  Dashboard,
  Impact,
  Matching,
  PostChallenge,
  ProfilePage,
  Teams,
  Workspace,
} from './pages/PlatformPages.jsx';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/challenges" element={<ChallengeHub />} />
          <Route element={<ProtectedRoute allowedRoles={['student', 'problem_owner', 'mentor', 'faculty', 'admin']} />}>
            <Route path="/matching" element={<Matching />} />
          </Route>
          <Route element={<ProtectedRoute allowedRoles={['student', 'faculty', 'admin']} />}>
            <Route path="/teams" element={<Teams />} />
          </Route>
          <Route element={<ProtectedRoute allowedRoles={['student', 'mentor', 'faculty', 'admin']} />}>
            <Route path="/workspace" element={<Workspace />} />
          </Route>
          <Route path="/impact" element={<Impact />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route element={<ProtectedRoute allowedRoles={['problem_owner', 'admin']} />}>
            <Route path="/owner" element={<PostChallenge />} />
          </Route>
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Route>
    </Routes>
  );
}