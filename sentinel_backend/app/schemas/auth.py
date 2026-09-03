from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
import re

class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    organization_name: str
    workspace_name: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r"[a-z]", v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r"\d", v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r"[!@#$%^&*()_+{}\[\]:;<>,.?~\\/-]", v):
            raise ValueError('Password must contain at least one special character')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    organization_id: str

class AuthMeResponse(BaseModel):
    user: UserResponse
    organization: dict
    workspace: dict

class GoogleLoginRequest(BaseModel):
    credential: str
