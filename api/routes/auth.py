"""
FinSentinel AI - Authentication Routes
JWT-based auth with RBAC support.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import jwt
import datetime
from config.settings import get_settings

router = APIRouter()
settings = get_settings()

# Demo users — replace with DB lookup in production
DEMO_USERS = {
    "analyst@finsentinel.com": {"password": "demo123", "role": "analyst"},
    "admin@finsentinel.com": {"password": "admin123", "role": "admin"},
    "auditor@finsentinel.com": {"password": "audit123", "role": "auditor"},
}


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
async def login(request: LoginRequest):
    user = DEMO_USERS.get(request.email)
    if not user or user["password"] != request.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    payload = {
        "sub": request.email,
        "role": user["role"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return {"access_token": token, "token_type": "bearer", "role": user["role"]}
