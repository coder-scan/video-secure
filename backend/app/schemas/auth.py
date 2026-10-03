from typing import Optional
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    organization_name: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    user_id: str
    tenant_id: str
    role: str
