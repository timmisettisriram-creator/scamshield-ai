"""
Auth — JWT, OTP with attempt tracking, Google OAuth.
"""
import os, random, time, secrets, hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import SECRET_KEY, ALGORITHM, TOKEN_TTL, OTP_TTL_SECONDS, OTP_MAX_ATTEMPTS, DEV_MODE_OTP

bearer_scheme = HTTPBearer(auto_error=False)

# ── In-memory OTP store (use Redis in production) ──────────────
# Structure: phone -> {otp_hash, expires, attempts, locked_until}
_otp_store: dict[str, dict] = {}

# ── JWT ────────────────────────────────────────────────────────
def create_token(user_id: str, email: str = "", name: str = "", avatar: str = "", phone: str = "") -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "name": name,
        "avatar": avatar,
        "phone": phone,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(seconds=TOKEN_TTL),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(creds.credentials)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return payload

def get_optional_user(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> Optional[dict]:
    if not creds:
        return None
    return decode_token(creds.credentials)

# ── OTP ────────────────────────────────────────────────────────
def _hash_otp(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()

def generate_otp(phone: str) -> str:
    record = _otp_store.get(phone, {})
    # Check if locked
    locked_until = record.get("locked_until", 0)
    if time.time() < locked_until:
        wait = int(locked_until - time.time())
        raise HTTPException(status_code=429, detail=f"Too many attempts. Try again in {wait} seconds.")

    otp = str(random.randint(100000, 999999))
    _otp_store[phone] = {
        "otp_hash": _hash_otp(otp),
        "expires": time.time() + OTP_TTL_SECONDS,
        "attempts": 0,
        "locked_until": 0,
    }
    return otp

def verify_otp(phone: str, otp: str) -> bool:
    record = _otp_store.get(phone)
    if not record:
        raise HTTPException(status_code=400, detail="OTP not found or expired. Please request a new one.")

    if time.time() > record["expires"]:
        del _otp_store[phone]
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

    record["attempts"] += 1

    if record["attempts"] > OTP_MAX_ATTEMPTS:
        record["locked_until"] = time.time() + 300  # 5 min lockout
        raise HTTPException(status_code=429, detail="Too many failed attempts. Account locked for 5 minutes.")

    if record["otp_hash"] != _hash_otp(otp):
        remaining = OTP_MAX_ATTEMPTS - record["attempts"]
        raise HTTPException(status_code=400, detail=f"Invalid OTP. {remaining} attempt(s) remaining.")

    del _otp_store[phone]
    return True

def upsert_user_memory(user_id: str, email: str = "", name: str = "", avatar: str = "", phone: str = "") -> dict:
    """Fallback in-memory user store (used when DB is unavailable)."""
    return {"id": user_id, "email": email, "name": name, "avatar": avatar, "phone": phone}
