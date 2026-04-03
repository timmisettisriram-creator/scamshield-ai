"""Auth routes — Google OAuth + Mobile OTP + profile management."""
import hashlib, httpx
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from auth import create_token, generate_otp, verify_otp, get_current_user
from database import get_db
from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, FRONTEND_URL, DEV_MODE_OTP
import crud

router = APIRouter(prefix="/auth", tags=["auth"])
GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO  = "https://www.googleapis.com/oauth2/v3/userinfo"

@router.get("/google")
async def google_login():
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(400, "Google OAuth not configured.")
    params = (f"?client_id={GOOGLE_CLIENT_ID}&redirect_uri={GOOGLE_REDIRECT_URI}"
              f"&response_type=code&scope=openid%20email%20profile&access_type=offline&prompt=select_account")
    return RedirectResponse(GOOGLE_AUTH_URL + params)

@router.get("/google/callback")
async def google_callback(code: str, db: AsyncSession = Depends(get_db)):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(400, "Google OAuth not configured.")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            tokens = (await client.post(GOOGLE_TOKEN_URL, data={
                "code": code, "client_id": GOOGLE_CLIENT_ID, "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI, "grant_type": "authorization_code"})).json()
            if "error" in tokens:
                raise HTTPException(400, tokens.get("error_description", "OAuth error"))
            user_info = (await client.get(GOOGLE_USERINFO,
                headers={"Authorization": f"Bearer {tokens['access_token']}"})).json()
    except httpx.TimeoutException:
        raise HTTPException(504, "Google OAuth timed out.")
    user_id = f"google_{user_info['sub']}"
    user = await crud.upsert_user(db, user_id=user_id, email=user_info.get("email",""),
        name=user_info.get("name",""), avatar=user_info.get("picture",""), provider="google")
    token = create_token(user_id, user.email or "", user.name or "", user.avatar or "")
    return RedirectResponse(f"{FRONTEND_URL}/?token={token}")

class OTPRequest(BaseModel):
    phone: str
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        clean = v.strip().replace("+91","").replace(" ","").replace("-","")
        if not clean.isdigit() or len(clean) != 10 or clean[0] not in "6789":
            raise ValueError("Enter a valid 10-digit Indian mobile number.")
        return clean

class OTPVerify(BaseModel):
    phone: str
    otp: str
    @field_validator("phone")
    @classmethod
    def vp(cls, v): return v.strip().replace("+91","").replace(" ","")
    @field_validator("otp")
    @classmethod
    def vo(cls, v):
        v = v.strip()
        if not v.isdigit() or len(v) != 6: raise ValueError("OTP must be 6 digits.")
        return v

@router.post("/otp/send")
async def send_otp(body: OTPRequest):
    otp = generate_otp(body.phone)
    import os, httpx as _httpx

    # ── Option 1: 2Factor.in (free trial, works immediately) ──
    twofactor_key = os.getenv("TWOFACTOR_API_KEY", "")
    if twofactor_key:
        try:
            async with _httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"https://2factor.in/API/V1/{twofactor_key}/SMS/+91{body.phone}/{otp}/ScamShieldOTP"
                )
                result = resp.json()
                if result.get("Status") == "Success":
                    return {"success": True, "message": f"OTP sent to +91 {body.phone}"}
                raise HTTPException(500, f"2Factor error: {result.get('Details', 'Unknown')}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"SMS failed: {str(e)[:100]}")

    # ── Option 2: Fast2SMS (needs website verification first) ──
    fast2sms_key = os.getenv("FAST2SMS_API_KEY", "")
    if fast2sms_key:
        try:
            async with _httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://www.fast2sms.com/dev/bulkV2",
                    headers={"authorization": fast2sms_key},
                    json={"route": "otp", "variables_values": otp,
                          "numbers": body.phone, "flash": 0}
                )
                result = resp.json()
                if result.get("return") is True:
                    return {"success": True, "message": f"OTP sent to +91 {body.phone}"}
                msgs = result.get("message", "Unknown error")
                err = msgs[0] if isinstance(msgs, list) and msgs else str(msgs)
                # If website verification needed, fall through to dev mode
                if "996" in str(result.get("status_code","")) or "verification" in err.lower():
                    pass  # fall through to dev mode
                else:
                    raise HTTPException(500, f"Fast2SMS: {err}")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"SMS failed: {str(e)[:100]}")

    # ── Option 3: Twilio ──────────────────────────────────────
    from config import TWILIO_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE, DEV_MODE_OTP
    if TWILIO_SID and TWILIO_AUTH_TOKEN and TWILIO_PHONE:
        try:
            from twilio.rest import Client
            Client(TWILIO_SID, TWILIO_AUTH_TOKEN).messages.create(
                body=f"Your ScamShield AI OTP is: {otp}\nValid 5 mins. Do not share.\n- ScamShield AI",
                from_=TWILIO_PHONE, to=f"+91{body.phone}")
            return {"success": True, "message": f"OTP sent to +91 {body.phone}"}
        except Exception as e:
            raise HTTPException(500, f"SMS failed: {str(e)[:100]}")

    # ── Dev mode — show OTP on screen ────────────────────────
    if DEV_MODE_OTP:
        return {"success": True, "dev_otp": otp,
                "message": f"[DEV] OTP: {otp} — Add TWOFACTOR_API_KEY to .env for real SMS"}
    return {"success": True, "message": "OTP sent."}
@router.post("/otp/verify")
async def verify_otp_route(body: OTPVerify, db: AsyncSession = Depends(get_db)):
    verify_otp(body.phone, body.otp)
    user_id = f"phone_{hashlib.md5(body.phone.encode()).hexdigest()[:12]}"
    user = await crud.upsert_user(db, user_id=user_id, phone=body.phone,
                                  name=f"+91 {body.phone}", provider="phone")
    token = create_token(user_id, user.email or "", user.name or "", phone=body.phone)
    return {"success": True, "token": token,
            "user": {"id": user.id, "name": user.name, "email": user.email,
                     "phone": user.phone, "avatar": user.avatar,
                     "safety_score": user.safety_score, "total_scans": user.total_scans}}

@router.get("/me")
async def me(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    db_user = await crud.get_user(db, user["sub"])
    if not db_user: return user
    return {"id": db_user.id, "name": db_user.name, "email": db_user.email,
            "phone": db_user.phone, "avatar": db_user.avatar, "provider": db_user.provider,
            "safety_score": db_user.safety_score, "total_scans": db_user.total_scans,
            "scams_caught": db_user.scams_caught, "created_at": db_user.created_at.isoformat()}

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None

@router.put("/me")
async def update_profile(body: ProfileUpdate, user=Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    db_user = await crud.get_user(db, user["sub"])
    if not db_user: raise HTTPException(404, "User not found")
    if body.name:  db_user.name  = body.name
    if body.email: db_user.email = body.email
    await db.commit()
    return {"success": True}

@router.delete("/me")
async def delete_account(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    db_user = await crud.get_user(db, user["sub"])
    if db_user:
        await db.delete(db_user)
        await db.commit()
    return {"success": True}

class AlertPrefs(BaseModel):
    email_alerts: bool = True
    sms_alerts: bool = False
    weekly_digest: bool = True

@router.put("/preferences")
async def update_preferences(body: AlertPrefs, user=Depends(get_current_user),
                              db: AsyncSession = Depends(get_db)):
    from models import AlertSetting
    from sqlalchemy import select
    r = await db.execute(select(AlertSetting).where(AlertSetting.user_id == user["sub"]))
    prefs = r.scalar_one_or_none()
    if not prefs:
        prefs = AlertSetting(user_id=user["sub"])
        db.add(prefs)
    prefs.email_alerts = body.email_alerts
    prefs.sms_alerts = body.sms_alerts
    prefs.weekly_digest = body.weekly_digest
    await db.commit()
    return {"success": True}

@router.get("/preferences")
async def get_preferences(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from models import AlertSetting
    from sqlalchemy import select
    r = await db.execute(select(AlertSetting).where(AlertSetting.user_id == user["sub"]))
    prefs = r.scalar_one_or_none()
    if not prefs:
        return {"email_alerts": True, "sms_alerts": False, "weekly_digest": True}
    return {"email_alerts": prefs.email_alerts, "sms_alerts": prefs.sms_alerts,
            "weekly_digest": prefs.weekly_digest}


