"""
Firebase Auth — verifies Firebase ID tokens from the frontend.
Frontend uses Firebase JS SDK to sign in, gets an ID token,
sends it to backend as Bearer token.
"""
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from firebase_config import verify_firebase_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    if not creds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return await verify_firebase_token(creds.credentials)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


async def get_optional_user(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> Optional[dict]:
    if not creds:
        return None
    try:
        return await verify_firebase_token(creds.credentials)
    except Exception:
        return None
