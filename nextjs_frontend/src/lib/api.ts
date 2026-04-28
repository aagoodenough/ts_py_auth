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

    const data = await response.json().catch(() => ({ detail: 'Unknown error' }));
    
    if (!response.ok || data.error) {
      throw new Error(data.error || data.detail || 'Request failed');
    }

    return data;
  }

  async register(email: string, password: string): Promise<AuthResponse> {
    const data = await this.request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    this.setToken(data.access_token);
    return data;
  }

  async login(email: string, password: string): Promise<AuthResponse> {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const response = await fetch(`${API_URL}/auth/jwt/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData,
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