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