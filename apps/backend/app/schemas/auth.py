from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.models.user import Role


class RegisterInstitutionRequest(BaseModel):
    institution_name: str = Field(..., min_length=2, max_length=255)
    institution_slug: str = Field(..., min_length=2, max_length=100)
    institution_domain: Optional[str] = None
    
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8)
    admin_first_name: str = Field(..., min_length=1)
    admin_last_name: str = Field(..., min_length=1)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    institution_slug: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str
