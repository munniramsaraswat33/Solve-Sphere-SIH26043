import React, { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';

const roleOptions = [
  { value: 'student', label: 'Student' },
  { value: 'problem-owner', label: 'Problem Owner' },
  { value: 'mentor', label: 'Industry Mentor' },
  { value: 'faculty', label: 'University / Faculty' },
];

function AuthFrame({ children, heading, subtitle }) {
  return (
    <main className="auth-page">
      <section aria-labelledby="auth-heading" className="auth-card">
        <Link className="auth-brand" to="/login"><span className="brandmark">◎</span>Solve Sphere</Link>
        <span className="auth-kicker">SIH26043 · Smart India Hackathon 2026</span>
        <h1 id="auth-heading">{heading}</h1>
        <p className="auth-subtitle">{subtitle}</p>
        {children}
      </section>
      <p className="auth-footer">Societal challenges, solved together.</p>
    </main>
  );
}

function apiErrorMessage(error) {
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join(' ');
  if (error.code === 'ECONNABORTED' || error.code === 'ETIMEDOUT') {
    return 'The API request timed out. Check that the backend and MongoDB are running, then try again.';
  }
  if (!error.response && error.request) {
    const baseURL = error.config?.baseURL || 'http://localhost:8000';
    const path = error.config?.url ?? '';
    const requestUrl = new URL(path, baseURL);
    return `No HTTP response was received from ${requestUrl.origin}${requestUrl.pathname}. This can be a connection problem or a CORS/browser network block. Check the backend log for this request and verify the frontend origin is allowed by CORS.`;
  }
  if (error.response?.status >= 500) {
    return `The API returned an error (HTTP ${error.response.status}). Check the backend logs and database connection, then try again.`;
  }
  if (error.response) {
    return `The API rejected the request (HTTP ${error.response.status}). Check the submitted information and try again.`;
  }
  return 'The request could not be completed. Check the API connection and try again.';
}

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const GOOGLE_SCRIPT_URL = 'https://accounts.google.com/gsi/client';
let googleScriptPromise;

function loadGoogleIdentityScript() {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (!googleScriptPromise) {
    googleScriptPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = GOOGLE_SCRIPT_URL;
      script.async = true;
      script.defer = true;
      script.onload = resolve;
      script.onerror = () => {
        googleScriptPromise = null;
        reject(new Error('Google sign-in could not be loaded. Check your connection and try again.'));
      };
      document.head.appendChild(script);
    });
  }
  return googleScriptPromise;
}

function GoogleSignInButton({ onCredential, onError }) {
  const buttonRef = useRef(null);
  const callbacks = useRef({ onCredential, onError });
  callbacks.current = { onCredential, onError };

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return undefined;
    let active = true;
    loadGoogleIdentityScript()
      .then(() => {
        if (!active || !buttonRef.current) return;
        buttonRef.current.replaceChildren();
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: ({ credential }) => {
            if (credential) callbacks.current.onCredential(credential);
            else callbacks.current.onError('Google did not return a sign-in credential. Please try again.');
          },
        });
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: 'outline',
          size: 'large',
          text: 'continue_with',
          shape: 'rectangular',
          width: Math.min(buttonRef.current.clientWidth || 480, 480),
        });
      })
      .catch((error) => {
        if (active) callbacks.current.onError(error.message);
      });
    return () => { active = false; };
  }, []);

  return GOOGLE_CLIENT_ID
    ? <div aria-label="Continue with Google" className="google-signin-slot" ref={buttonRef} />
    : <button className="btn google-signin-fallback" onClick={() => onError('Google sign-in is not configured. Set VITE_GOOGLE_CLIENT_ID in frontend/.env and GOOGLE_CLIENT_ID in backend/.env, then restart both servers.')} type="button">
      <span aria-hidden="true" className="google-g">G</span>Continue with Google
    </button>;
}

function PasswordInput({ label, name, value, onChange, autoComplete, minLength, required }) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="password-field">
      <label htmlFor={`auth-${name}`}>{label}</label>
      <span className="password-input-wrap">
        <input
          id={`auth-${name}`}
          autoComplete={autoComplete}
          minLength={minLength}
          name={name}
          onChange={onChange}
          required={required}
          type={visible ? 'text' : 'password'}
          value={value}
        />
        <button
          aria-label={`${visible ? 'Hide' : 'Show'} ${name === 'confirmPassword' ? 'confirm password' : 'password'}`}
          aria-pressed={visible}
          className="password-visibility-toggle"
          onMouseDown={(event) => event.preventDefault()}
          onClick={() => setVisible((current) => !current)}
          type="button"
        >
          {visible ? (
            <svg aria-hidden="true" viewBox="0 0 24 24">
              <path d="M3 3l18 18M10.6 10.6a2 2 0 002.8 2.8" />
              <path d="M9.9 5.2A10.8 10.8 0 0112 5c5 0 8.5 4.5 9.5 6-.4.6-1.3 1.8-2.8 3M6.2 6.2C3.9 7.6 2.7 9.6 2.5 11c1 1.5 4.5 6 9.5 6 1 0 1.9-.2 2.7-.5" />
            </svg>
          ) : (
            <svg aria-hidden="true" viewBox="0 0 24 24">
              <path d="M2.5 12S6 6 12 6s9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6z" />
              <circle cx="12" cy="12" r="2.5" />
            </svg>
          )}
        </button>
      </span>
    </div>
  );
}

function AuthDivider() {
  return <div className="auth-divider"><span>or</span></div>;
}

export function LoginPage() {
  const { login, googleLogin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState(location.state?.notice ?? '');
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await login({ email, password });
      navigate(location.state?.from?.pathname ?? '/dashboard', { replace: true });
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGoogleCredential(idToken) {
    setError('');
    setSubmitting(true);
    try {
      await googleLogin(idToken);
      navigate(location.state?.from?.pathname ?? '/dashboard', { replace: true });
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthFrame heading="Welcome back" subtitle="Sign in to continue your work on Solve Sphere.">
      {notice && <p className="auth-notice" role="status">{notice}</p>}
      <form className="auth-form" onSubmit={handleSubmit}>
        <label>Email address<input autoComplete="email" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} /></label>
        <PasswordInput autoComplete="current-password" label="Password" minLength="10" name="password" onChange={(event) => setPassword(event.target.value)} required value={password} />
        {error && <p className="auth-error" role="alert">{error}</p>}
        <button className="btn primary auth-submit" disabled={submitting} type="submit">{submitting ? 'Signing in…' : 'Sign in'}</button>
      </form>
      <AuthDivider />
      <GoogleSignInButton onCredential={handleGoogleCredential} onError={setError} />
      <p className="auth-switch">New to Solve Sphere? <Link to="/register">Create an account</Link></p>
      <p className="auth-admin-note">Administrator accounts are provisioned by the platform operator.</p>
    </AuthFrame>
  );
}

function FormField({ label, name, onChange, type = 'text', ...props }) {
  return <label>{label}<input name={name} onChange={onChange} type={type} {...props} /></label>;
}

export function RegisterPage() {
  const { register, googleLogin } = useAuth();
  const navigate = useNavigate();
  const [role, setRole] = useState('student');
  const [fields, setFields] = useState({});
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  function updateField(event) {
    setFields((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    const form = new FormData(event.currentTarget);
    const account = {
      email: form.get('email'),
      password: form.get('password'),
      ...(form.get('name') ? { name: form.get('name') } : {}),
    };

    if (account.password !== form.get('confirmPassword')) {
      setError('Passwords do not match.');
      setSubmitting(false);
      return;
    }

    try {
      await register(role, account);
      navigate('/dashboard', { replace: true });
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleGoogleCredential(idToken) {
    setError('');
    setSubmitting(true);
    try {
      await googleLogin(idToken, role.replace('-', '_'));
      navigate('/dashboard', { replace: true });
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthFrame heading="Create your account" subtitle="Join the people turning societal challenges into solutions.">
      <form className="auth-form" onSubmit={handleSubmit}>
        <label>Account role<select onChange={(event) => setRole(event.target.value)} value={role}>{roleOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
        <FormField autoComplete="name" label="Full name (optional)" name="name" onChange={updateField} value={fields.name ?? ''} />
        <FormField autoComplete="email" label="Email address" name="email" onChange={updateField} required type="email" value={fields.email ?? ''} />
        <div className="auth-grid">
          <PasswordInput autoComplete="new-password" label="Password (10+ characters)" minLength="10" name="password" onChange={updateField} required value={fields.password ?? ''} />
          <PasswordInput autoComplete="new-password" label="Confirm password" minLength="10" name="confirmPassword" onChange={updateField} required value={fields.confirmPassword ?? ''} />
        </div>
        {error && <p className="auth-error" role="alert">{error}</p>}
        <button className="btn primary auth-submit" disabled={submitting} type="submit">{submitting ? 'Creating account…' : 'Create account'}</button>
      </form>
      <AuthDivider />
      <GoogleSignInButton onCredential={handleGoogleCredential} onError={setError} />
      <p className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></p>
      <p className="auth-admin-note">Admin access is provisioned by the platform operator.</p>
    </AuthFrame>
  );
}