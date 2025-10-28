"""
Authentication models
"""
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: str


class LoginRequest(BaseModel):
    username: str
    password: str


class User(BaseModel):
    user_id: str
    username: str
    email: str = None