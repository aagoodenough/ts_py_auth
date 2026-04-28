'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';

function GoogleCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState('');

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get('code');
      if (!code) {
        setError('No authorization code received');
        return;
      }

      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${API_URL}/auth/oauth/google/callback?code=${code}`);
        const data = await response.json();

        if (data.access_token) {
          localStorage.setItem('auth_token', data.access_token);
          router.push('/dashboard');
        } else {
          setError(data.error || 'Authentication failed');
        }
      } catch (err: any) {
        setError(err?.message || 'Authentication failed');
      }
    };

    handleCallback();
  }, [searchParams, router]);

  if (error) {
    return (
      <div className="container">
        <div className="card">
          <p className="error">{error}</p>
          <a href="/" className="link">Return to login</a>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <p>Completing sign in...</p>
    </div>
  );
}

export default function GoogleCallbackPage() {
  return (
    <Suspense fallback={<div className="container"><p>Loading...</p></div>}>
      <GoogleCallbackContent />
    </Suspense>
  );
}