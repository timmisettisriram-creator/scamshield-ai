"""
Centralised config — reads from .env file or environment variables.
"""
import os, secrets
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ── Core ───────────────────────────────────────────────────────
SECRET_KEY   = os.getenv("SECRET_KEY", secrets.token_hex(32))
ALGORITHM    = "HS256"
TOKEN_TTL    = int(os.getenv("TOKEN_TTL_HOURS", "24")) * 3600
ENVIRONMENT  = os.getenv("ENVIRONMENT", "development")
IS_PROD      = ENVIRONMENT == "production"

# ── Database ───────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./scamshield.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

# ── Frontend ───────────────────────────────────────────────────
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8000")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://localhost:3000").split(",")

# ── Google OAuth ───────────────────────────────────────────────
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", f"{FRONTEND_URL}/auth/google/callback")

# ── Twilio SMS ─────────────────────────────────────────────────
TWILIO_SID        = os.getenv("TWILIO_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE      = os.getenv("TWILIO_PHONE", "")

# ── URL Reputation APIs ────────────────────────────────────────
GOOGLE_SAFE_BROWSING_KEY = os.getenv("GOOGLE_SAFE_BROWSING_KEY", "")
VIRUSTOTAL_KEY           = os.getenv("VIRUSTOTAL_KEY", "")

# ── Sentry ─────────────────────────────────────────────────────
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

# ── Firebase ───────────────────────────────────────────────────
FIREBASE_PROJECT_ID      = os.getenv("FIREBASE_PROJECT_ID", "safe-fire-ai1")
FIREBASE_SERVICE_ACCOUNT = os.getenv("FIREBASE_SERVICE_ACCOUNT", "")

# ── Rate limits ────────────────────────────────────────────────
RATE_LIMIT_ANALYZE  = os.getenv("RATE_LIMIT_ANALYZE",  "30/minute")
RATE_LIMIT_OTP      = os.getenv("RATE_LIMIT_OTP",      "5/minute")
RATE_LIMIT_DEFAULT  = os.getenv("RATE_LIMIT_DEFAULT",  "60/minute")

# ── OTP ────────────────────────────────────────────────────────
OTP_TTL_SECONDS  = int(os.getenv("OTP_TTL_SECONDS", "300"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "5"))
DEV_MODE_OTP     = not IS_PROD  # show OTP in response in dev
