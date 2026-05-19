'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { authAPI } from '@/lib/api';

declare global {
  interface Window {
    grecaptcha: {
      render: (elementId: string, options: { sitekey: string; theme: string; callback?: Function; 'expired-callback'?: Function; 'error-callback'?: Function }) => number;
      getResponse: (widgetId: number) => string;
      reset: (widgetId?: number) => void;
    };
  }
}

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const siteKey = process.env.NEXT_PUBLIC_RECAPTCHA_SITE_KEY || '';
    const initRecaptcha = () => {
      if (siteKey && window.grecaptcha && !window.grecaptcha.render) {
        setTimeout(initRecaptcha, 100);
        return;
      }
      if (siteKey && window.grecaptcha && window.grecaptcha.render) {
        const container = document.getElementById('recaptcha-register');
        if (container && !container.hasChildNodes()) {
          const widgetId = window.grecaptcha.render('recaptcha-register', {
            sitekey: siteKey,
            theme: 'light',
          });
          (window as any).__recaptchaRegisterWidgetId = widgetId;
        }
      }
    };
    if (window.grecaptcha) {
      initRecaptcha();
    } else {
      window.onload = initRecaptcha;
    }
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);

    try {
      const widgetId = (window as any).__recaptchaRegisterWidgetId;
      const recaptchaToken = window.grecaptcha.getResponse(widgetId);
      if (!recaptchaToken) {
        setError('Please complete the reCAPTCHA');
        setLoading(false);
        return;
      }
      await authAPI.register(email, password, recaptchaToken);
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <div className="card">
        <h1>Create Account</h1>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem' }}>
              Minimum 8 characters, 1 uppercase, 1 special character
            </p>
          </div>

          <div className="form-group">
            <label htmlFor="confirmPassword">Confirm Password</label>
            <input
              id="confirmPassword"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>

          <div className="g-recaptcha-wrapper">
            <div id="recaptcha-register"></div>
          </div>

          {error && <p className="error">{error}</p>}

          <button type="submit" disabled={loading}>
            {loading ? 'Creating account...' : 'Sign Up'}
          </button>
        </form>

        <Link href="/" className="link">
          Already have an account? Sign in
        </Link>
      </div>
    </div>
  );
}