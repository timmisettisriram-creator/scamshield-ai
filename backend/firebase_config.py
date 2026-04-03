"""
Firebase Admin SDK initialization.
Falls back gracefully if credentials are not configured.
"""
import os, json
import firebase_admin
from firebase_admin import credentials

_initialized = False
_firebase_available = False


def init_firebase() -> bool:
    global _initialized, _firebase_available
    if _initialized:
        return _firebase_available

    sa_json = os.getenv("FIREBASE_SERVICE_ACCOUNT", "").strip()
    sa_path = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")

    cred = None
    if sa_json:
        try:
            sa_dict = json.loads(sa_json)
            cred = credentials.Certificate(sa_dict)
        except Exception:
            pass
    if cred is None and os.path.exists(sa_path):
        try:
            cred = credentials.Certificate(sa_path)
        except Exception:
            pass

    if cred is None:
        _initialized = True
        _firebase_available = False
        return False

    try:
        if not len(firebase_admin._apps):
            firebase_admin.initialize_app(cred, {
                "projectId": os.getenv("FIREBASE_PROJECT_ID", "safe-fire-ai1"),
            })
        _firebase_available = True
    except Exception:
        _firebase_available = False

    _initialized = True
    return _firebase_available


def is_firebase_available() -> bool:
    return _firebase_available


def get_firestore():
    if not _firebase_available:
        raise RuntimeError("Firebase not configured")
    from firebase_admin import firestore_async
    return firestore_async.client()


def get_fb_auth():
    if not _firebase_available:
        raise RuntimeError("Firebase not configured")
    from firebase_admin import auth
    return auth


async def verify_firebase_token(id_token: str) -> dict:
    if not _firebase_available:
        raise ValueError("Firebase not configured")
    from firebase_admin import auth
    try:
        return auth.verify_id_token(id_token)
    except Exception as e:
        raise ValueError(f"Invalid Firebase token: {e}")
