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
    
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        if provider == "google":
            existing_user.google_id = provider_id
        elif provider == "github":
            existing_user.github_id = provider_id
        existing_user.is_oauth_user = True
        existing_user.oauth_email = email
        await session.commit()
        await session.refresh(existing_user)
        return existing_user
    
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
    state: str | None = None,
    request: Request = None,
    session: AsyncSession = Depends(get_async_session),
):
    try:
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
            
            if "error" in tokens:
                return {"error": tokens.get("error_description", tokens.get("error", "Token exchange failed"))}
            
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
    except Exception as e:
        return {"error": str(e)}


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
    state: str | None = None,
    session: AsyncSession = Depends(get_async_session),
):
    try:
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
            
            if "error" in tokens:
                return {"error": tokens.get("error_description", tokens.get("error", "Token exchange failed"))}
            
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
    except Exception as e:
        return {"error": str(e)}