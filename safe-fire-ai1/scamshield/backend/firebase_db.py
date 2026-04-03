"""
Firestore database operations — replaces SQLAlchemy crud.py for Firebase.
All data stored in Firestore collections.
"""
from datetime import datetime, timezone
from firebase_config import get_firestore
from google.cloud.firestore_v1 import AsyncDocumentReference


def _now():
    return datetime.now(timezone.utc)


# ── Collections ────────────────────────────────────────────────
USERS       = "users"
SCANS       = "scans"
REPORTS     = "scam_reports"
ENTITIES    = "known_entities"
NEWSLETTER  = "newsletter"
CONTACTS    = "contacts"
BOOKMARKS   = "bookmarks"


# ── Users ──────────────────────────────────────────────────────
async def get_user(uid: str) -> dict | None:
    db = get_firestore()
    doc = await db.collection(USERS).document(uid).get()
    return doc.to_dict() if doc.exists else None


async def upsert_user(uid: str, **kwargs) -> dict:
    db = get_firestore()
    ref = db.collection(USERS).document(uid)
    doc = await ref.get()
    if doc.exists:
        update = {k: v for k, v in kwargs.items() if v}
        update["last_login"] = _now()
        await ref.update(update)
        data = doc.to_dict()
        data.update(update)
    else:
        data = {
            "id": uid,
            "email": kwargs.get("email", ""),
            "phone": kwargs.get("phone", ""),
            "name": kwargs.get("name", ""),
            "avatar": kwargs.get("avatar", ""),
            "provider": kwargs.get("provider", "phone"),
            "is_verified": False,
            "is_admin": False,
            "safety_score": 100,
            "total_scans": 0,
            "scams_caught": 0,
            "created_at": _now(),
            "last_login": _now(),
        }
        await ref.set(data)
    return data


async def update_user_stats(uid: str, verdict: str):
    db = get_firestore()
    ref = db.collection(USERS).document(uid)
    doc = await ref.get()
    if not doc.exists:
        return
    d = doc.to_dict()
    total = d.get("total_scans", 0) + 1
    scams = d.get("scams_caught", 0) + (1 if verdict == "SCAM" else 0)
    safety = max(0, int(100 - (scams / total) * 60))
    await ref.update({"total_scans": total, "scams_caught": scams, "safety_score": safety})


# ── Scans ──────────────────────────────────────────────────────
async def create_scan(user_id: str = None, **kwargs) -> dict:
    db = get_firestore()
    data = {
        "user_id": user_id,
        "created_at": _now(),
        **kwargs,
    }
    ref = await db.collection(SCANS).add(data)
    data["id"] = ref[1].id
    return data


async def get_user_scans(uid: str, limit: int = 20) -> list[dict]:
    db = get_firestore()
    docs = (db.collection(SCANS)
              .where("user_id", "==", uid)
              .order_by("created_at", direction="DESCENDING")
              .limit(limit))
    results = []
    async for doc in docs.stream():
        d = doc.to_dict()
        d["id"] = doc.id
        results.append(d)
    return results


async def get_scan_stats() -> dict:
    db = get_firestore()
    # Firestore doesn't support COUNT natively in free tier — use aggregation
    total_ref = db.collection(SCANS)
    scam_ref  = db.collection(SCANS).where("verdict", "==", "SCAM")
    total_docs = await total_ref.count().get()
    scam_docs  = await scam_ref.count().get()
    total = total_docs[0][0].value if total_docs else 0
    scams = scam_docs[0][0].value  if scam_docs  else 0
    return {
        "total_scanned": total,
        "scams_detected": scams,
        "today_scans": 0,  # would need a date filter
        "unique_phones_flagged": 0,
        "unique_upi_flagged": 0,
        "unique_domains_flagged": 0,
    }


# ── Reports ────────────────────────────────────────────────────
async def create_report(**kwargs) -> dict:
    db = get_firestore()
    data = {
        "upvotes": 0,
        "is_verified": False,
        "is_flagged": False,
        "created_at": _now(),
        **kwargs,
    }
    ref = await db.collection(REPORTS).add(data)
    data["id"] = ref[1].id
    return data


async def get_reports(limit: int = 20, scam_type: str = None, state: str = None) -> list[dict]:
    db = get_firestore()
    q = db.collection(REPORTS).where("is_flagged", "==", False)
    if scam_type:
        q = q.where("scam_type", "==", scam_type)
    q = q.order_by("created_at", direction="DESCENDING").limit(limit)
    results = []
    async for doc in q.stream():
        d = doc.to_dict()
        d["id"] = doc.id
        results.append(d)
    return results


async def upvote_report(report_id: str, ip: str = None) -> bool:
    db = get_firestore()
    ref = db.collection(REPORTS).document(report_id)
    doc = await ref.get()
    if not doc.exists:
        return False
    d = doc.to_dict()
    await ref.update({"upvotes": d.get("upvotes", 0) + 1})
    return True


# ── Known Entities ─────────────────────────────────────────────
async def lookup_entity(entity_type: str, value: str) -> dict | None:
    db = get_firestore()
    docs = (db.collection(ENTITIES)
              .where("entity_type", "==", entity_type)
              .where("entity_value", "==", value.lower())
              .limit(1))
    async for doc in docs.stream():
        d = doc.to_dict()
        d["id"] = doc.id
        return d
    return None


async def upsert_entity(entity_type: str, value: str, scam_type: str, risk_score: int = 80):
    db = get_firestore()
    existing = await lookup_entity(entity_type, value)
    if existing:
        ref = db.collection(ENTITIES).document(existing["id"])
        await ref.update({
            "report_count": existing.get("report_count", 1) + 1,
            "risk_score": min(existing.get("risk_score", 80) + 5, 100),
        })
    else:
        await db.collection(ENTITIES).add({
            "entity_type": entity_type,
            "entity_value": value.lower(),
            "scam_type": scam_type,
            "risk_score": risk_score,
            "report_count": 1,
            "is_verified": False,
            "source": "community",
            "added_at": _now(),
        })


async def bulk_lookup(phones: list, upi_ids: list, domains: list) -> dict:
    hits = []
    total = 0
    for phone in phones:
        e = await lookup_entity("phone", phone)
        if e:
            hits.append(f"Phone {phone}: {e['report_count']} reports ({e['scam_type']})")
            total += e["report_count"]
    for upi in upi_ids:
        e = await lookup_entity("upi", upi)
        if e:
            hits.append(f"UPI {upi}: {e['report_count']} reports ({e['scam_type']})")
            total += e["report_count"]
    for domain in domains:
        e = await lookup_entity("domain", domain)
        if e:
            hits.append(f"Domain {domain}: {e['report_count']} reports ({e['scam_type']})")
            total += e["report_count"]
    return {"prior_reports": total, "hits": hits}


async def get_graph_data() -> dict:
    db = get_firestore()
    nodes = [{"id": "root", "label": "🛡️ ScamShield DB", "group": "root"}]
    links = []
    icon_map = {"phone": "📞", "upi": "💳", "domain": "🌐", "email": "📧", "company": "🏢"}
    async for doc in db.collection(ENTITIES).limit(80).stream():
        e = doc.to_dict()
        nid = f"{e['entity_type']}_{e['entity_value']}"
        nodes.append({
            "id": nid,
            "label": f"{icon_map.get(e['entity_type'],'❓')} {e['entity_value']}",
            "group": e["entity_type"],
            "reports": e.get("report_count", 1),
            "risk": e.get("risk_score", 80),
        })
        links.append({"source": "root", "target": nid, "reports": e.get("report_count", 1)})
    return {"nodes": nodes, "links": links}


# ── Newsletter ─────────────────────────────────────────────────
async def subscribe_newsletter(email: str) -> bool:
    db = get_firestore()
    ref = db.collection(NEWSLETTER).document(email)
    doc = await ref.get()
    if doc.exists:
        await ref.update({"is_active": True})
        return False
    await ref.set({"email": email, "is_active": True, "created_at": _now()})
    return True


# ── Contact ────────────────────────────────────────────────────
async def save_contact(name: str, email: str, subject: str, message: str):
    db = get_firestore()
    await db.collection(CONTACTS).add({
        "name": name, "email": email, "subject": subject,
        "message": message, "is_read": False, "created_at": _now(),
    })


# ── Bookmarks ──────────────────────────────────────────────────
async def add_bookmark(uid: str, scan_id: str, note: str = "") -> dict:
    db = get_firestore()
    data = {"user_id": uid, "scan_id": scan_id, "note": note, "created_at": _now()}
    ref = await db.collection(BOOKMARKS).add(data)
    data["id"] = ref[1].id
    return data


async def get_bookmarks(uid: str) -> list[dict]:
    db = get_firestore()
    results = []
    async for doc in (db.collection(BOOKMARKS)
                        .where("user_id", "==", uid)
                        .order_by("created_at", direction="DESCENDING")
                        .stream()):
        d = doc.to_dict()
        d["id"] = doc.id
        results.append(d)
    return results
