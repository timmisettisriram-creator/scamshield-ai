"""
Firebase Auth Routes — profile management.
Auth itself (Google, Phone OTP) is handled entirely by Firebase JS SDK on frontend.
Backend just verifies the ID token and manages user profiles in Firestore.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from firebase_auth import get_current_user
import firebase_db as db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def me(user=Depends(get_current_user)):
    """Get current user profile from Firestore."""
    uid = user["uid"]
    profile = await db.get_user(uid)
    if not profile:
        # Auto-create profile from Firebase token claims
        profile = await db.upsert_user(
            uid=uid,
            email=user.get("email", ""),
            name=user.get("name", ""),
            avatar=user.get("picture", ""),
            phone=user.get("phone_number", ""),
            provider=user.get("firebase", {}).get("sign_in_provider", "unknown"),
        )
    return profile


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


@router.put("/me")
async def update_profile(body: ProfileUpdate, user=Depends(get_current_user)):
    uid = user["uid"]
    updates = {k: v for k, v in body.model_dump().items() if v}
    if updates:
        from firebase_config import get_firestore
        fs = get_firestore()
        await fs.collection("users").document(uid).update(updates)
    return {"success": True}


@router.delete("/me")
async def delete_account(user=Depends(get_current_user)):
    uid = user["uid"]
    from firebase_config import get_firestore, get_fb_auth
    fs = get_firestore()
    # Delete Firestore data
    await fs.collection("users").document(uid).delete()
    # Delete Firebase Auth user
    try:
        get_fb_auth().delete_user(uid)
    except Exception:
        pass
    return {"success": True}


class AlertPrefs(BaseModel):
    email_alerts: bool = True
    sms_alerts: bool = False
    weekly_digest: bool = True


@router.put("/preferences")
async def update_preferences(body: AlertPrefs, user=Depends(get_current_user)):
    from firebase_config import get_firestore
    fs = get_firestore()
    await fs.collection("user_preferences").document(user["uid"]).set(body.model_dump())
    return {"success": True}


@router.get("/preferences")
async def get_preferences(user=Depends(get_current_user)):
    from firebase_config import get_firestore
    fs = get_firestore()
    doc = await fs.collection("user_preferences").document(user["uid"]).get()
    if doc.exists:
        return doc.to_dict()
    return {"email_alerts": True, "sms_alerts": False, "weekly_digest": True}
