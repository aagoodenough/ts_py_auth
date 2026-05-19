const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface User {
  id: string;
  email: string;
  is_active: boolean;
  is_verified: boolean;
  is_superuser: boolean;
  is_oauth_user: boolean;
  oauth_email: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user?: User;
}

class AuthAPI {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('auth_token', token);
    } else {
      localStorage.removeItem('auth_token');
    }
  }

  getToken(): string | null {
    if (!this.token) {
      this.token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
    }
    return this.token;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    const token = this.getToken();
    if (token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || 'Request failed');
    }

    return response.json();
  }

  async register(email: string, password: string, recaptchaToken?: string): Promise<AuthResponse> {
    const response = await fetch(`${API_URL}/auth/register-with-recaptcha`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        password,
        recaptcha_token: recaptchaToken,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Registration failed' }));
      throw new Error(error.detail || 'Registration failed');
    }

    const data = await response.json();
    this.setToken(data.access_token);
    return data;
  }

  async login(email: string, password: string, recaptchaToken?: string): Promise<AuthResponse> {
    const response = await fetch(`${API_URL}/auth/login-with-recaptcha`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email,
        password,
        recaptcha_token: recaptchaToken,
      }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Invalid credentials' }));
      throw new Error(error.detail || 'Login failed');
    }

    const data = await response.json();
    this.setToken(data.access_token);
    return data;
  }

  async logout(): Promise<void> {
    this.setToken(null);
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>('/users/me');
  }

  async googleLogin(): Promise<{ authorization_url: string }> {
    return this.request<{ authorization_url: string }>('/auth/oauth/google');
  }

  async githubLogin(): Promise<{ authorization_url: string }> {
    return this.request<{ authorization_url: string }>('/auth/oauth/github');
  }

  async handleOAuthCallback(provider: string, code: string): Promise<AuthResponse> {
    return this.request<AuthResponse>(`/auth/oauth/${provider}/callback?code=${code}`);
  }
}

export const authAPI = new AuthAPI();