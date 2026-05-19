# ПРИЛОЖЕНИЕ. ЛИСТИНГ ПРОГРАММНОГО КОДА

---

## 1. BACKEND (FastAPI)

### 1.1. Конфигурация (config.py)

```python
from typing import Set

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    OPENAPI_URL: str = "/openapi.json"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/postgres"
    TEST_DATABASE_URL: str | None = None
    EXPIRE_ON_COMMIT: bool = False

    SUPABASE_URL: str = "https://your-project.supabase.co"
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    ACCESS_SECRET_KEY: str
    RESET_PASSWORD_SECRET_KEY: str
    VERIFICATION_SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_SECONDS: int = 3600

    MAIL_USERNAME: str | None = None
    MAIL_PASSWORD: str | None = None
    MAIL_FROM: str | None = None
    MAIL_SERVER: str | None = None
    MAIL_PORT: int | None = None
    MAIL_FROM_NAME: str = "FastAPI template"
    MAIL_STARTTLS: bool = True
    MAIL_SSL_TLS: bool = False
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True
    TEMPLATE_DIR: str = "email_templates"

    FRONTEND_URL: str = "http://localhost:3000"

    CORS_ORIGINS: Set[str] = {"http://localhost:3000"}

    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
```

### 1.2. Модели базы данных (models.py)

```python
from datetime import datetime
from typing import Optional

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    __allow_unmapped__ = True
    
    google_id: Optional[str] = Column(String, nullable=True, unique=True, index=True)
    github_id: Optional[str] = Column(String, nullable=True, unique=True, index=True)
    oauth_email: Optional[str] = Column(String, nullable=True)
    is_oauth_user: bool = Column(Boolean, default=False)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, is_oauth={self.is_oauth_user})>"
```

### 1.3. Подключение к базе данных (database.py)

```python
from typing import AsyncGenerator
from urllib.parse import urlparse

from fastapi import Depends
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings
from .models import Base, User


parsed_db_url = urlparse(settings.DATABASE_URL)

async_db_connection_url = (
    f"postgresql+asyncpg://{parsed_db_url.username}:{parsed_db_url.password}@"
    f"{parsed_db_url.hostname}{':' + str(parsed_db_url.port) if parsed_db_url.port else ''}"
    f"{parsed_db_url.path}"
)

engine = create_async_engine(async_db_connection_url, poolclass=NullPool)

async_session_maker = async_sessionmaker(
    engine, expire_on_commit=settings.EXPIRE_ON_COMMIT
)


async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)
```

### 1.4. Pydantic схемы (schemas.py)

```python
import uuid

from fastapi_users import schemas
from pydantic import BaseModel
from uuid import UUID


class UserRead(schemas.BaseUser[uuid.UUID]):
    is_oauth_user: bool = False
    oauth_email: str | None = None


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass


class OAuthUserCreate(BaseModel):
    email: str
    provider: str
    provider_id: str
    name: str | None = None

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class OAuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
```

### 1.5. Менеджер пользователей и JWT (users.py)

```python
import uuid
import re

from typing import Optional

from fastapi import Depends, Request
from fastapi_users import (
    BaseUserManager,
    FastAPIUsers,
    UUIDIDMixin,
    InvalidPasswordException,
)

from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase

from .config import settings
from .database import get_user_db
from .models import User
from .schemas import UserCreate

AUTH_URL_PATH = "auth"


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.RESET_PASSWORD_SECRET_KEY
    verification_token_secret = settings.VERIFICATION_SECRET_KEY

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} forgot password. Token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id}. Token: {token}")

    async def validate_password(
        self,
        password: str,
        user: UserCreate,
    ) -> None:
        errors = []

        if len(password) < 8:
            errors.append("Password should be at least 8 characters.")
        if user.email in password:
            errors.append("Password should not contain e-mail.")
        if not any(char.isupper() for char in password):
            errors.append("Password should contain at least one uppercase letter.")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password should contain at least one special character.")

        if errors:
            raise InvalidPasswordException(reason=errors)


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


bearer_transport = BearerTransport(tokenUrl=f"{AUTH_URL_PATH}/jwt/login")


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(
        secret=settings.ACCESS_SECRET_KEY,
        lifetime_seconds=settings.ACCESS_TOKEN_EXPIRE_SECONDS,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
```

### 1.6. OAuth обработчики (oauth.py)

```python
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, Request
from fastapi_users import fastapi_users
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_async_session
from .models import User
from .schemas import UserRead, TokenResponse
from .users import auth_backend, get_jwt_strategy

router = APIRouter(prefix="/auth/oauth", tags=["oauth"])


GOOGLE_CLIENT_ID = settings.GOOGLE_CLIENT_ID or ""
GOOGLE_CLIENT_SECRET = settings.GOOGLE_CLIENT_SECRET or ""
GITHUB_CLIENT_ID = settings.GITHUB_CLIENT_ID or ""
GITHUB_CLIENT_SECRET = settings.GITHUB_CLIENT_SECRET or ""

GOOGLE_OAUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

GITHUB_OAUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USERINFO_URL = "https://api.github.com/user"


async def get_user_by_oauth(session: AsyncSession, provider: str, provider_id: str) -> Optional[User]:
    stmt = select(User)
    if provider == "google":
        stmt = stmt.where(User.google_id == provider_id)
    elif provider == "github":
        stmt = stmt.where(User.github_id == provider_id)
    
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_or_create_oauth_user(
    session: AsyncSession,
    provider: str,
    provider_id: str,
    email: str,
    name: Optional[str] = None,
) -> User:
    user = await get_user_by_oauth(session, provider, provider_id)
    
    if user:
        return user
    
    user_id = uuid4()
    user_data = {
        "id": user_id,
        "email": email,
        "hashed_password": "",
        "is_active": True,
        "is_superuser": False,
        "is_verified": True,
    }
    
    if provider == "google":
        user_data["google_id"] = provider_id
    elif provider == "github":
        user_data["github_id"] = provider_id
    
    user = User(**user_data, oauth_email=email, is_oauth_user=True)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    
    return user


async def create_jwt_token(user: User) -> str:
    strategy = get_jwt_strategy()
    return await strategy.write_token(user)


@router.get("/google")
async def google_oauth_redirect(request: Request):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return {"error": "Google OAuth not configured"}
    
    state = str(uuid4())
    request.session["oauth_state"] = state
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": f"{settings.FRONTEND_URL}/auth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }
    
    import urllib.parse
    auth_url = f"{GOOGLE_OAUTH_URL}?{urllib.parse.urlencode(params)}"
    
    return {"authorization_url": auth_url}


@router.get("/google/callback")
async def google_oauth_callback(
    code: str,
    state: str,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return {"error": "Google OAuth not configured"}
    
    import httpx
    import urllib.parse
    
    token_data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": f"{settings.FRONTEND_URL}/auth/google/callback",
    }
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(GOOGLE_TOKEN_URL, data=token_data)
        tokens = token_response.json()
        
        access_token = tokens.get("access_token")
        
        user_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_info = user_response.json()
    
    user = await get_or_create_oauth_user(
        session=session,
        provider="google",
        provider_id=user_info.get("id", ""),
        email=user_info.get("email", ""),
        name=user_info.get("name"),
    )
    
    jwt_token = await create_jwt_token(user)
    
    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": UserRead.model_validate(user),
    }


@router.get("/github")
async def github_oauth_redirect(request: Request):
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        return {"error": "GitHub OAuth not configured"}
    
    state = str(uuid4())
    request.session["oauth_state"] = state
    
    params = {
        "client_id": GITHUB_CLIENT_ID,
        "redirect_uri": f"{settings.FRONTEND_URL}/auth/github/callback",
        "scope": "user:email",
        "state": state,
    }
    
    import urllib.parse
    auth_url = f"{GITHUB_OAUTH_URL}?{urllib.parse.urlencode(params)}"
    
    return {"authorization_url": auth_url}


@router.get("/github/callback")
async def github_oauth_callback(
    code: str,
    state: str,
    session: AsyncSession = Depends(get_async_session),
):
    if not GITHUB_CLIENT_ID or not GITHUB_CLIENT_SECRET:
        return {"error": "GitHub OAuth not configured"}
    
    import httpx
    import urllib.parse
    
    token_data = {
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "code": code,
    }
    
    headers = {"Accept": "application/json"}
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(GITHUB_TOKEN_URL, data=token_data, headers=headers)
        tokens = token_response.json()
        
        access_token = tokens.get("access_token")
        
        user_response = await client.get(
            GITHUB_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        user_info = user_response.json()
        
        emails_response = await client.get(
            "https://api.github.com/user/emails",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        emails = emails_response.json()
        
        primary_email = next((e["email"] for e in emails if e.get("primary")), user_info.get("email"))
    
    user = await get_or_create_oauth_user(
        session=session,
        provider="github",
        provider_id=str(user_info.get("id", "")),
        email=primary_email or "unknown@github.local",
        name=user_info.get("name") or user_info.get("login"),
    )
    
    jwt_token = await create_jwt_token(user)
    
    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": UserRead.model_validate(user),
    }
```

### 1.7. Главный файл приложения (main.py)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import create_db_and_tables
from .schemas import UserCreate, UserRead, UserUpdate
from .users import auth_backend, fastapi_users, AUTH_URL_PATH
from .oauth import router as oauth_router

app = FastAPI(
    title="Auth API",
    description="Authentication API with OAuth support",
    openapi_url=settings.OPENAPI_URL,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://ts-py-auth.vercel.app",
        "https://ts-py-auth.onrender.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await create_db_and_tables()


app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix=f"/{AUTH_URL_PATH}/jwt",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix=f"/{AUTH_URL_PATH}",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_reset_password_router(),
    prefix=f"/{AUTH_URL_PATH}",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_verify_router(UserRead),
    prefix=f"/{AUTH_URL_PATH}",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

app.include_router(oauth_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### 1.8. Зависимости Python (requirements.txt)

```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
pydantic>=2.6.0
pydantic-settings>=2.1.0
sqlalchemy[asyncio]>=2.0.0
asyncpg>=0.29.0
fastapi-users[sqlalchemy]>=12.0.0
python-jose[cryptography]>=3.3.0
httpx>=0.26.0
python-multipart>=0.0.9
```

---

## 2. FRONTEND (Next.js)

### 2.1. API клиент (lib/api.ts)

```typescript
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
    const data = await this.request<AuthResponse>(`/auth/oauth/${provider}/callback?code=${code}`);
    this.setToken(data.access_token);
    return data;
  }
}

export const authAPI = new AuthAPI();
```

### 2.2. Страница входа (app/page.tsx)

```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { authAPI } from '@/lib/api';

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await authAPI.login(email, password);
      router.push('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    try {
      const { authorization_url } = await authAPI.googleLogin();
      window.location.href = authorization_url;
    } catch (err) {
      setError('Google login is not configured');
    }
  };

  const handleGitHubLogin = async () => {
    try {
      const { authorization_url } = await authAPI.githubLogin();
      window.location.href = authorization_url;
    } catch (err) {
      setError('GitHub login is not configured');
    }
  };

  return (
    <div className="container">
      <div className="card">
        <h1>Sign In</h1>
        
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
          </div>

          {error && <p className="error">{error}</p>}

          <button type="submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div className="divider">
          <span>or continue with</span>
        </div>

        <div className="oauth-buttons">
          <button type="button" className="oauth-btn" onClick={handleGoogleLogin}>
            <svg width="20" height="20" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Continue with Google
          </button>

          <button type="button" className="oauth-btn" onClick={handleGitHubLogin}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
            </svg>
            Continue with GitHub
          </button>
        </div>

        <Link href="/register" className="link">
          Don&apos;t have an account? Sign up
        </Link>
      </div>
    </div>
  );
}
```

### 2.3. Страница регистрации (app/register/page.tsx)

```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { authAPI } from '@/lib/api';

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

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
      await authAPI.register(email, password);
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
```

### 2.4. Защищённый дашборд (app/dashboard/page.tsx)

```typescript
'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { authAPI, User } from '@/lib/api';

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchUser = async () => {
      const token = authAPI.getToken();
      if (!token) {
        router.push('/');
        return;
      }

      try {
        const userData = await authAPI.getCurrentUser();
        setUser(userData);
      } catch (err) {
        authAPI.logout();
        router.push('/');
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, [router]);

  const handleLogout = async () => {
    await authAPI.logout();
    router.push('/');
  };

  if (loading) {
    return (
      <div className="container">
        <p>Loading...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container">
        <p className="error">{error}</p>
      </div>
    );
  }

  return (
    <div className="container">
      <div className="card">
        <div className="dashboard-header">
          <h1>Dashboard</h1>
        </div>

        {user && (
          <div className="user-info">
            <p><strong>Email:</strong> {user.email}</p>
            <p><strong>ID:</strong> {user.id}</p>
            <p><strong>Verified:</strong> {user.is_verified ? 'Yes' : 'No'}</p>
            <p><strong>OAuth User:</strong> {user.is_oauth_user ? 'Yes' : 'No'}</p>
            {user.oauth_email && (
              <p><strong>OAuth Email:</strong> {user.oauth_email}</p>
            )}
          </div>
        )}

        <button className="logout-btn" onClick={handleLogout}>
          Sign Out
        </button>
      </div>
    </div>
  );
}
```

### 2.5. OAuth callback Google (app/auth/google/callback/page.tsx)

```typescript
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
```

### 2.6. OAuth callback GitHub (app/auth/github/callback/page.tsx)

```typescript
'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { authAPI } from '@/lib/api';

function GitHubCallbackContent() {
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
        await authAPI.handleOAuthCallback('github', code);
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

export default function GitHubCallbackPage() {
  return (
    <Suspense fallback={<div className="container"><p>Loading...</p></div>}>
      <GitHubCallbackContent />
    </Suspense>
  );
}
```

### 2.7. Корневой layout (app/layout.tsx)

```typescript
import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Auth App',
  description: 'Authentication application with OAuth support',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

### 2.8. Стили (app/globals.css)

```css
:root {
  --primary: #2563eb;
  --primary-hover: #1d4ed8;
  --background: #ffffff;
  --foreground: #171717;
  --muted: #6b7280;
  --border: #e5e7eb;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: var(--background);
  color: var(--foreground);
  line-height: 1.6;
}

.container {
  max-width: 400px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.card {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

h1 {
  font-size: 1.5rem;
  font-weight: 600;
  margin-bottom: 1.5rem;
  text-align: center;
}

.form-group {
  margin-bottom: 1rem;
}

label {
  display: block;
  font-size: 0.875rem;
  font-weight: 500;
  margin-bottom: 0.5rem;
}

input {
  width: 100%;
  padding: 0.625rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 1rem;
}

input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

button {
  width: 100%;
  padding: 0.75rem;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

button:hover {
  background: var(--primary-hover);
}

button:disabled {
  background: var(--muted);
  cursor: not-allowed;
}

.oauth-buttons {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.oauth-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.625rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: white;
  color: var(--foreground);
  font-size: 0.875rem;
  cursor: pointer;
  transition: background 0.2s;
}

.oauth-btn:hover {
  background: #f9fafb;
}

.divider {
  display: flex;
  align-items: center;
  margin: 1.5rem 0;
}

.divider::before,
.divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--border);
}

.divider span {
  padding: 0 0.75rem;
  color: var(--muted);
  font-size: 0.875rem;
}

.error {
  color: #dc2626;
  font-size: 0.875rem;
  margin-top: 0.5rem;
  text-align: center;
}

.link {
  display: block;
  text-align: center;
  margin-top: 1rem;
  color: var(--primary);
  text-decoration: none;
  font-size: 0.875rem;
}

.link:hover {
  text-decoration: underline;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--border);
}

.user-info {
  background: #f9fafb;
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
}

.user-info p {
  margin: 0.25rem 0;
}

.logout-btn {
  background: #dc2626;
}

.logout-btn:hover {
  background: #b91c1c;
}
```

### 2.9. Зависимости Frontend (package.json)

```json
{
  "name": "nextjs-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "14.1.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/node": "^20.11.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "typescript": "^5.3.0"
  }
}
```

---

## 3. ФАЙЛ КОНФИГУРАЦИИ (.env.example)

```
DATABASE_URL=postgresql+asyncpg://postgres:password@host:5432/postgres

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

ACCESS_SECRET_KEY=your-super-secret-key-for-jwt
RESET_PASSWORD_SECRET_KEY=your-reset-password-secret
VERIFICATION_SECRET_KEY=your-verification-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_SECONDS=3600

FRONTEND_URL=http://localhost:3000

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

---

*Конец листинга*