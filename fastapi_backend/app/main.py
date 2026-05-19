from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

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


class RecaptchaVerifyRequest(BaseModel):
    token: str


async def verify_recaptcha_token(token: str) -> bool:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://www.google.com/recaptcha/api/siteverify",
            data={
                "secret": settings.RECAPTCHA_SECRET_KEY,
                "response": token,
            },
        )
        result = response.json()
        return result.get("success", False)


class LoginWithRecaptchaRequest(BaseModel):
    email: str
    password: str
    recaptcha_token: str


@app.post("/auth/login-with-recaptcha")
async def login_with_recaptcha(request: LoginWithRecaptchaRequest):
    if not await verify_recaptcha_token(request.recaptcha_token):
        raise HTTPException(status_code=400, detail="reCAPTCHA verification failed")

    from .users import get_user_manager
    from .database import get_user_db
    from fastapi_users.password import verify_password

    async for user_db in get_user_db():
        async for user_manager in get_user_manager(user_db):
            user = await user_manager.user_db.get_by_email(request.email)
            if not user or not user.hashed_password:
                raise HTTPException(status_code=400, detail="Invalid credentials")

            if not await verify_password(request.password, user.hashed_password):
                raise HTTPException(status_code=400, detail="Invalid credentials")

            from .users import auth_backend
            from fastapi_users.jwt import generate_jwt

            jwt_payload = {
                "sub": str(user.id),
                "email": user.email,
            }
            token = await generate_jwt(
                jwt_payload,
                auth_backend.get_strategy().secret,
                auth_backend.get_strategy().lifetime_seconds,
            )

            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "is_superuser": user.is_superuser,
                },
            }


class RegisterWithRecaptchaRequest(BaseModel):
    email: str
    password: str
    recaptcha_token: str


@app.post("/auth/register-with-recaptcha")
async def register_with_recaptcha(request: RegisterWithRecaptchaRequest):
    if not await verify_recaptcha_token(request.recaptcha_token):
        raise HTTPException(status_code=400, detail="reCAPTCHA verification failed")

    from .users import get_user_manager
    from .database import get_user_db
    from .schemas import UserCreate

    async for user_db in get_user_db():
        async for user_manager in get_user_manager(user_db):
            try:
                user = await user_manager.create(UserCreate(email=request.email, password=request.password))
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e))

            from .users import auth_backend
            from fastapi_users.jwt import generate_jwt

            jwt_payload = {
                "sub": str(user.id),
                "email": user.email,
            }
            token = await generate_jwt(
                jwt_payload,
                auth_backend.get_strategy().secret,
                auth_backend.get_strategy().lifetime_seconds,
            )

            return {
                "access_token": token,
                "token_type": "bearer",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "is_superuser": user.is_superuser,
                },
            }