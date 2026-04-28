'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { authAPI } from '@/lib/api';

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
        await authAPI.handleOAuthCallback('google', code);
        router.push('/dashboard');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Authentication failed');
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