from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime


# Request schemas
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    consent_processing: bool = False

    @field_validator("phone", mode="before")
    @classmethod
    def phone_empty_to_none(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return v.strip() if isinstance(v, str) else v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    preferred_language: Optional[str] = None  # 'ru' | 'uz'

    @field_validator("email", mode="before")
    @classmethod
    def email_empty_to_none(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return v.strip() if isinstance(v, str) else v

    @field_validator("full_name", "phone", mode="before")
    @classmethod
    def strip_empty_to_none(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        return v.strip() if isinstance(v, str) else v


# Response schemas
class UserResponse(BaseModel):
    id: UUID
    email: Optional[str]
    full_name: Optional[str]
    phone: Optional[str]
    is_active: bool
    created_at: datetime
    is_admin: bool = False
    preferred_language: Optional[str] = None  # 'ru' | 'uz'

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: UserResponse


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
