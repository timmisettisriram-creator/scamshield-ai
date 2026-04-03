"""
ScamShield AI — Production Backend v4.0
Auto-detects Firebase vs SQLite based on available credentials.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Request, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import base64, os, time, asyncio

from config import (ALLOWED_ORIGINS, IS_PROD, SENTRY_DSN,
                    RATE_LIMIT_ANALYZE, RATE_LIMIT_DEFAULT)
from database import AsyncSessionLocal as _db_session
from schemas import AnalysisRequest, SafetyScorecard
from nlp_engine import analyze_text
from infra_audit import audit_domain, extract_domain
from scorecard import build_scorecard
from ocr_engine import extract_text_from_image
from email_intel import analyze_email_context
from url_reputation import analyze_urls
from pattern_store import record_analysis, get_repeat_score, get_stats as get_pattern_stats
from logger import setup_logging, log

if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(dsn=SENTRY_DSN, traces_sample_rate=0.1)

setup_logging()
limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT_DEFAULT])

# ── Detect backend: Firebase or SQLite ────────────────────────
from firebase_config import init_firebase, is_firebase_available
_USE_FIREBASE = init_firebase()

if _USE_FIREBASE:
    import firebase_db as db
    from firebase_auth import get_optional_user, get_current_user
    from firebase_auth_routes import router as auth_router
    log.info("backend_mode", mode="firebase", project="safe-fire-ai1")
else:
    # Fall back to SQLite
    from database import init_db, get_db
    import crud as _crud
    from auth import get_optional_user, get_current_user
    from auth_routes import router as auth_router
    log.info("backend_mode", mode="sqlite",
             note="Add serviceAccountKey.json to enable Firebase")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if _USE_FIREBASE:
        try:
            from firebase_seed import seed
            await seed()
        except Exception as e:
            log.warning("firebase_seed_failed", error=str(e))
    else:
        await init_db()
        try:
            from seed_db import seed
            await seed()
        except Exception as e:
            log.warning("sqlite_seed_failed", error=str(e))
    log.info("startup_complete", version="4.0.0",
             db="firebase" if _USE_FIREBASE else "sqlite")
    yield


app = FastAPI(
    title="ScamShield AI",
    description="AI-powered scam detection for India's job seekers",
    version="4.0.0",
    docs_url="/docs" if not IS_PROD else None,
    redoc_url="/redoc" if not IS_PROD else None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["X-Process-Time"] = f"{(time.time()-start)*1000:.1f}ms"
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(status_code=500,
        content={"detail": "An internal error occurred. Please try again."})


# ── Unified DB helpers (works for both Firebase and SQLite) ────
async def _db_create_scan(**kwargs):
    if _USE_FIREBASE:
        return await db.create_scan(**kwargs)
    async with _db_session() as session:
        return await _crud.create_scan(session, **kwargs)

async def _db_update_user_stats(uid, verdict):
    if _USE_FIREBASE:
        return await db.update_user_stats(uid, verdict)
    async with _db_session() as session:
        return await _crud.update_user_stats(session, uid, verdict)

async def _db_create_report(**kwargs):
    if _USE_FIREBASE:
        return await db.create_report(**kwargs)
    async with _db_session() as session:
        return await _crud.create_report(session, **kwargs)

async def _db_upsert_entity(t, v, st):
    if _USE_FIREBASE:
        return await db.upsert_entity(t, v, st)
    async with _db_session() as session:
        return await _crud.upsert_entity(session, t, v, st)

async def _db_bulk_lookup(phones, upi_ids, domains):
    if _USE_FIREBASE:
        return await db.bulk_lookup(phones, upi_ids, domains)
    async with _db_session() as session:
        return await _crud.bulk_lookup(session, phones, upi_ids, domains)

async def _db_get_reports(limit, scam_type, state):
    if _USE_FIREBASE:
        return await db.get_reports(limit=limit, scam_type=scam_type, state=state)
    async with _db_session() as session:
        return await _crud.get_reports(session, limit=limit, scam_type=scam_type, state=state)

async def _db_upvote_report(report_id, ip):
    if _USE_FIREBASE:
        return await db.upvote_report(str(report_id), ip=ip)
    async with _db_session() as session:
        return await _crud.upvote_report(session, int(report_id), ip=ip)

async def _db_get_stats():
    if _USE_FIREBASE:
        return await db.get_scan_stats()
    async with _db_session() as session:
        return await _crud.get_scan_stats(session)

async def _db_graph_data():
    if _USE_FIREBASE:
        return await db.get_graph_data()
    async with _db_session() as session:
        from models import KnownScamEntity
        from sqlalchemy import select
        r = await session.execute(select(KnownScamEntity).limit(80))
        entities = r.scalars().all()
        nodes = [{"id": "root", "label": "🛡️ ScamShield DB", "group": "root"}]
        links = []
        icon_map = {"phone":"📞","upi":"💳","domain":"🌐","email":"📧","company":"🏢"}
        for e in entities:
            nid = f"{e.entity_type}_{e.entity_value}"
            nodes.append({"id": nid, "label": f"{icon_map.get(e.entity_type,'❓')} {e.entity_value}",
                          "group": e.entity_type, "reports": e.report_count, "risk": e.risk_score})
            links.append({"source": "root", "target": nid, "reports": e.report_count})
        return {"nodes": nodes, "links": links}

async def _db_lookup_entity(type_, value):
    if _USE_FIREBASE:
        return await db.lookup_entity(type_, value)
    async with _db_session() as session:
        e = await _crud.lookup_entity(session, type_, value)
        if not e: return None
        return {"scam_type": e.scam_type, "risk_score": e.risk_score,
                "report_count": e.report_count, "is_verified": e.is_verified}

async def _db_get_user_scans(uid, limit):
    if _USE_FIREBASE:
        return await db.get_user_scans(uid, limit=limit)
    async with _db_session() as session:
        scans = await _crud.get_user_scans(session, uid, limit=limit)
        return [{"id": s.id, "verdict": s.verdict, "risk_score": s.risk_score,
                 "input_text": s.input_text, "language": s.language,
                 "created_at": s.created_at.isoformat()} for s in scans]

async def _db_subscribe_newsletter(email):
    if _USE_FIREBASE:
        return await db.subscribe_newsletter(email)
    async with _db_session() as session:
        return await _crud.subscribe_newsletter(session, email)

async def _db_save_contact(name, email, subject, message):
    if _USE_FIREBASE:
        return await db.save_contact(name, email, subject, message)
    async with _db_session() as session:
        return await _crud.save_contact(session, name, email, subject, message)


# ── Core analysis ──────────────────────────────────────────────
async def _run_analysis(text: str, domain: str = None, image_b64: str = None,
                        user_id: str = None, ip: str = None) -> SafetyScorecard:
    if image_b64:
        ocr = extract_text_from_image(image_b64)
        text = (ocr.get("text", "") + " " + (text or "")).strip()

    if not text and not domain:
        raise HTTPException(422, "Provide text, domain, or image to analyze.")

    text = (text or "")[:5000]
    nlp = analyze_text(text)

    domain_to_check = domain
    if not domain_to_check and nlp.get("urls"):
        domain_to_check = extract_domain(nlp["urls"][0])

    infra = {}
    if domain_to_check:
        try:
            infra = await asyncio.wait_for(
                asyncio.to_thread(audit_domain, domain_to_check), timeout=8.0)
        except asyncio.TimeoutError:
            pass

    graph       = await _db_bulk_lookup(nlp.get("phones",[]), nlp.get("upi_ids",[]), nlp.get("domains",[]))
    email_intel = analyze_email_context(text)
    url_rep     = await analyze_urls(nlp.get("urls", []))
    pattern     = get_repeat_score(text, nlp.get("phones",[]), nlp.get("upi_ids",[]), nlp.get("domains",[]))

    result = build_scorecard(nlp, infra, graph, email_intel, url_rep, pattern)

    try:
        await _db_create_scan(
            user_id=user_id, input_text=text[:2000], input_domain=domain,
            verdict=result.verdict, risk_score=result.overall_risk,
            category_scores=result.category_scores,
            factors=[f.model_dump() for f in result.factors],
            language=result.language,
            phones_found=nlp.get("phones",[]), upi_found=nlp.get("upi_ids",[]),
            urls_found=nlp.get("urls",[]), emails_found=nlp.get("emails",[]),
            ip_address=ip,
        )
        if user_id:
            await _db_update_user_stats(user_id, result.verdict)

        if result.verdict == "SCAM":
            scam_type = ("Telegram Task Scam" if nlp.get("telegram_task") else
                         "Phishing Attempt"   if nlp.get("phishing") else
                         "Upfront Fee Scam"   if nlp.get("fee_request") else
                         "Salary Bait Scam"   if nlp.get("salary_bait") else
                         "Brand Impersonation" if nlp.get("impersonated_brands") else
                         "Scam Detected")
            await _db_create_report(
                scam_type=scam_type, snippet=text[:150], full_text=text[:2000],
                risk_score=result.overall_risk, verdict=result.verdict,
                phones=nlp.get("phones",[]), upi_ids=nlp.get("upi_ids",[]),
                domains=nlp.get("domains",[]),
            )
            for phone in nlp.get("phones", []):
                await _db_upsert_entity("phone", phone, scam_type)
            for upi in nlp.get("upi_ids", []):
                await _db_upsert_entity("upi", upi, scam_type)
            for dom in nlp.get("domains", []):
                await _db_upsert_entity("domain", dom, scam_type)
    except Exception as e:
        log.error("db_write_failed", error=str(e))

    record_analysis(text, result.verdict, result.overall_risk,
                    nlp.get("phones",[]), nlp.get("upi_ids",[]),
                    nlp.get("urls",[]), nlp.get("domains",[]))
    return result


@app.post("/analyze", response_model=SafetyScorecard)
@limiter.limit(RATE_LIMIT_ANALYZE)
async def analyze(req: AnalysisRequest, request: Request,
                  user=Depends(get_optional_user)):
    ip = request.client.host if request.client else None
    uid = user.get("uid") or user.get("sub") if user else None
    return await _run_analysis(text=req.text or "", domain=req.domain,
                               image_b64=req.image_base64, user_id=uid, ip=ip)


@app.post("/analyze/image")
@limiter.limit(RATE_LIMIT_ANALYZE)
async def analyze_image(request: Request, file: UploadFile = File(...),
                        user=Depends(get_optional_user)):
    if file.content_type not in ("image/jpeg","image/png","image/webp","image/gif"):
        raise HTTPException(415, "Only JPEG, PNG, WebP images supported.")
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(413, "Image too large. Max 10MB.")
    b64 = base64.b64encode(contents).decode()
    ip = request.client.host if request.client else None
    uid = user.get("uid") or user.get("sub") if user else None
    return await _run_analysis(image_b64=b64, user_id=uid, ip=ip)


# ── Reports ────────────────────────────────────────────────────
@app.get("/reports")
@limiter.limit(RATE_LIMIT_DEFAULT)
async def list_reports(request: Request,
    limit: int = Query(20, ge=1, le=100),
    scam_type: Optional[str] = None,
    state: Optional[str] = None):
    reports = await _db_get_reports(limit, scam_type, state)
    return [_fmt_report(r) for r in reports]


def _fmt_report(r) -> dict:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    # Handle both Firestore Timestamp and datetime objects
    created = r.get("created_at") if isinstance(r, dict) else getattr(r, "created_at", None)
    try:
        if hasattr(created, "timestamp"):
            diff = int(now.timestamp() - created.timestamp())
        elif hasattr(created, "isoformat"):
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            diff = int((now - created).total_seconds())
        else:
            diff = 3600
    except Exception:
        diff = 3600

    if diff < 3600:    ts = f"{max(diff//60,1)}m ago"
    elif diff < 86400: ts = f"{diff//3600}h ago"
    else:              ts = f"{diff//86400}d ago"

    if isinstance(r, dict):
        return {"id": r.get("id",""), "type": r.get("scam_type","Unknown"),
                "snippet": r.get("snippet",""), "location": r.get("location","India"),
                "state": r.get("state"), "risk": r.get("risk_score",0),
                "verdict": r.get("verdict","SCAM"), "upvotes": r.get("upvotes",0),
                "is_verified": r.get("is_verified",False), "time": ts}
    else:
        return {"id": r.id, "type": r.scam_type, "snippet": r.snippet,
                "location": r.location, "state": r.state, "risk": r.risk_score,
                "verdict": r.verdict, "upvotes": r.upvotes,
                "is_verified": r.is_verified, "time": ts}


class ReportSubmit(BaseModel):
    type: str
    snippet: str
    location: Optional[str] = "India"
    state: Optional[str] = None
    risk: int
    verdict: str


@app.post("/reports")
@limiter.limit("10/minute")
async def submit_report(request: Request, body: ReportSubmit):
    r = await _db_create_report(scam_type=body.type, snippet=body.snippet[:200],
        location=body.location, state=body.state, risk_score=body.risk, verdict=body.verdict)
    return _fmt_report(r)


@app.post("/reports/{report_id}/upvote")
@limiter.limit("5/minute")
async def upvote(report_id: str, request: Request):
    ip = request.client.host if request.client else None
    ok = await _db_upvote_report(report_id, ip)
    return {"success": ok}


# ── Stats ──────────────────────────────────────────────────────
@app.get("/stats")
async def platform_stats():
    fs_stats = await _db_get_stats()
    return {**fs_stats, **get_pattern_stats()}


@app.get("/stats/trends")
async def scan_trends(days: int = Query(30, ge=1, le=90)):
    if not _USE_FIREBASE:
        async with _db_session() as session:
            return await _crud.get_scan_trends(session, days=days)
    return []  # Firebase trends coming soon


@app.get("/stats/scam-types")
async def scam_type_breakdown():
    if not _USE_FIREBASE:
        from sqlalchemy import func, select
        from models import ScamReport
        async with _db_session() as session:
            r = await session.execute(
                select(ScamReport.scam_type, func.count(ScamReport.id).label("count"))
                .group_by(ScamReport.scam_type).order_by(func.count(ScamReport.id).desc()).limit(10))
            return [{"type": row.scam_type, "count": row.count} for row in r]
    return []


# ── Trust graph ────────────────────────────────────────────────
@app.get("/graph/data")
async def graph_data():
    return await _db_graph_data()


# ── Entity lookup ──────────────────────────────────────────────
@app.get("/lookup")
@limiter.limit("30/minute")
async def lookup_entity(request: Request, type: str, value: str):
    entity = await _db_lookup_entity(type, value)
    if not entity:
        return {"found": False, "risk_score": 0}
    return {"found": True, **entity}


# ── User scans ─────────────────────────────────────────────────
@app.get("/scans/my")
async def my_scans(user=Depends(get_current_user),
                   limit: int = Query(20, ge=1, le=100)):
    uid = user.get("uid") or user.get("sub")
    return await _db_get_user_scans(uid, limit)


# ── Bookmarks ──────────────────────────────────────────────────
@app.post("/bookmarks")
async def add_bookmark(scan_id: str, note: str = "", user=Depends(get_current_user)):
    uid = user.get("uid") or user.get("sub")
    if _USE_FIREBASE:
        bm = await db.add_bookmark(uid, scan_id, note)
        return {"success": True, "id": bm.get("id")}
    async with _db_session() as session:
        bm = await _crud.add_bookmark(session, uid, int(scan_id), note)
        return {"success": True, "id": bm.id}


@app.get("/bookmarks")
async def get_bookmarks(user=Depends(get_current_user)):
    uid = user.get("uid") or user.get("sub")
    if _USE_FIREBASE:
        return await db.get_bookmarks(uid)
    async with _db_session() as session:
        bms = await _crud.get_bookmarks(session, uid)
        return [{"id": b.id, "scan_id": b.scan_id, "note": b.note} for b in bms]


# ── Newsletter ─────────────────────────────────────────────────
class NewsletterReq(BaseModel):
    email: EmailStr


@app.post("/newsletter/subscribe")
@limiter.limit("3/minute")
async def newsletter_subscribe(request: Request, body: NewsletterReq):
    is_new = await _db_subscribe_newsletter(str(body.email))
    return {"success": True, "is_new": is_new}


# ── Contact ────────────────────────────────────────────────────
class ContactReq(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str


@app.post("/contact")
@limiter.limit("3/minute")
async def contact(request: Request, body: ContactReq):
    if len(body.message) < 10:
        raise HTTPException(422, "Message too short.")
    await _db_save_contact(body.name, str(body.email), body.subject, body.message)
    return {"success": True, "message": "Message received. We'll respond within 24 hours."}


# ── Firebase token exchange (Google sign-in from frontend) ─────
class FirebaseTokenReq(BaseModel):
    id_token: str

@app.post("/auth/firebase-token")
async def firebase_token_exchange(body: FirebaseTokenReq):
    """Exchange a Firebase ID token for our backend JWT."""
    try:
        from firebase_config import verify_firebase_token, is_firebase_available
        if not is_firebase_available():
            raise HTTPException(503, "Firebase not configured on backend")
        claims = await verify_firebase_token(body.id_token)
        uid = claims["uid"]
        user_data = {
            "id": uid,
            "name": claims.get("name", ""),
            "email": claims.get("email", ""),
            "avatar": claims.get("picture", ""),
            "phone": claims.get("phone_number", ""),
        }
        from auth import create_token
        token = create_token(uid, user_data["email"], user_data["name"], user_data["avatar"])
        return {"success": True, "token": token, "user": user_data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(401, f"Invalid Firebase token: {str(e)[:80]}")


# ── Health ─────────────────────────────────────────────────────
@app.get("/health")
async def health():
    db_status = "firebase" if _USE_FIREBASE else "sqlite"
    if _USE_FIREBASE:
        try:
            fs = get_firestore()
            await fs.collection("_health").document("ping").get()
            db_status = "firebase_ok"
        except Exception as e:
            db_status = f"firebase_error"
    else:
        try:
            from database import engine
            from sqlalchemy import text
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_status = "sqlite_ok"
        except Exception:
            db_status = "sqlite_error"
    return {"status": "ok", "version": "4.0.0", "db": db_status,
            "firebase_ready": _USE_FIREBASE, "service": "ScamShield AI"}


# ── Serve frontend ─────────────────────────────────────────────
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    static_path = os.path.join(frontend_path, "static")
    if os.path.exists(static_path):
        app.mount("/static", StaticFiles(directory=static_path), name="static")

    def _serve(f): return FileResponse(os.path.join(frontend_path, f))

    @app.get("/",        include_in_schema=False)
    async def serve_index():   return _serve("index.html")
    @app.get("/auth",    include_in_schema=False)
    async def serve_auth():    return _serve("auth.html")
    @app.get("/login",   include_in_schema=False)
    async def serve_login():   return _serve("auth.html")
    @app.get("/privacy", include_in_schema=False)
    async def serve_privacy(): return _serve("privacy.html")
    @app.get("/terms",   include_in_schema=False)
    async def serve_terms():   return _serve("terms.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        if full_path == "auth": return _serve("auth.html")
        page = os.path.join(frontend_path, f"{full_path}.html")
        if os.path.exists(page): return FileResponse(page)
        return _serve("index.html")
