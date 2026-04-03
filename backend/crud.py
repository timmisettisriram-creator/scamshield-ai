"""
CRUD operations — all DB interactions go through here.
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, update, and_, or_, Integer as SAInteger
from sqlalchemy.sql.expression import cast
from models import (
    User, ScanRecord, ScamReport, ReportUpvote,
    KnownScamEntity, Bookmark, AlertSetting,
    NewsletterSubscriber, ContactMessage, ScamTrend
)
import hashlib


# ── Users ──────────────────────────────────────────────────────
async def get_user(db: AsyncSession, user_id: str) -> User | None:
    return await db.get(User, user_id)

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    r = await db.execute(select(User).where(User.email == email))
    return r.scalar_one_or_none()

async def get_user_by_phone(db: AsyncSession, phone: str) -> User | None:
    r = await db.execute(select(User).where(User.phone == phone))
    return r.scalar_one_or_none()

async def upsert_user(db: AsyncSession, user_id: str, email: str = "",
                      name: str = "", avatar: str = "", phone: str = "",
                      provider: str = "phone") -> User:
    user = await get_user(db, user_id)
    if not user:
        user = User(id=user_id, email=email or None, name=name,
                    avatar=avatar, phone=phone or None, provider=provider)
        db.add(user)
    else:
        if name:   user.name   = name
        if avatar: user.avatar = avatar
        user.last_login = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    return user

async def update_user_stats(db: AsyncSession, user_id: str, verdict: str):
    user = await get_user(db, user_id)
    if not user: return
    user.total_scans += 1
    if verdict == "SCAM": user.scams_caught += 1
    # Recalculate safety score
    if user.total_scans > 0:
        scam_ratio = user.scams_caught / user.total_scans
        user.safety_score = max(0, int(100 - scam_ratio * 60))
    await db.commit()


# ── Scan Records ───────────────────────────────────────────────
async def create_scan(db: AsyncSession, **kwargs) -> ScanRecord:
    scan = ScanRecord(**kwargs)
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return scan

async def get_user_scans(db: AsyncSession, user_id: str, limit: int = 20) -> list[ScanRecord]:
    r = await db.execute(
        select(ScanRecord).where(ScanRecord.user_id == user_id)
        .order_by(desc(ScanRecord.created_at)).limit(limit)
    )
    return r.scalars().all()

async def get_scan_stats(db: AsyncSession) -> dict:
    total = await db.scalar(select(func.count(ScanRecord.id)))
    scams = await db.scalar(select(func.count(ScanRecord.id)).where(ScanRecord.verdict == "SCAM"))
    today = datetime.now(timezone.utc).date().isoformat()
    today_count = await db.scalar(
        select(func.count(ScanRecord.id))
        .where(func.date(ScanRecord.created_at) == today)
    )
    return {
        "total_scanned": total or 0,
        "scams_detected": scams or 0,
        "today_scans": today_count or 0,
        "unique_phones_flagged": 0,
        "unique_upi_flagged": 0,
        "unique_domains_flagged": 0,
    }

async def get_scan_trends(db: AsyncSession, days: int = 30) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    r = await db.execute(
        select(
            func.date(ScanRecord.created_at).label("date"),
            func.count(ScanRecord.id).label("total"),
            func.sum(cast(ScanRecord.verdict == "SCAM", SAInteger)).label("scams"),
        )
        .where(func.date(ScanRecord.created_at) >= since)
        .group_by(func.date(ScanRecord.created_at))
        .order_by("date")
    )
    return [{"date": row.date, "total": row.total, "scams": row.scams or 0} for row in r]


# ── Scam Reports ───────────────────────────────────────────────
async def create_report(db: AsyncSession, **kwargs) -> ScamReport:
    report = ScamReport(**kwargs)
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report

async def get_reports(db: AsyncSession, limit: int = 20, scam_type: str = None,
                      state: str = None) -> list[ScamReport]:
    q = select(ScamReport).where(ScamReport.is_flagged == False)
    if scam_type: q = q.where(ScamReport.scam_type == scam_type)
    if state:     q = q.where(ScamReport.state == state)
    q = q.order_by(desc(ScamReport.created_at)).limit(limit)
    r = await db.execute(q)
    return r.scalars().all()

async def upvote_report(db: AsyncSession, report_id: int,
                        user_id: str = None, ip: str = None) -> bool:
    # Prevent duplicate upvotes
    q = select(ReportUpvote).where(ReportUpvote.report_id == report_id)
    if user_id: q = q.where(ReportUpvote.user_id == user_id)
    elif ip:    q = q.where(ReportUpvote.ip_address == ip)
    existing = await db.scalar(q)
    if existing: return False

    db.add(ReportUpvote(report_id=report_id, user_id=user_id, ip_address=ip))
    report = await db.get(ScamReport, report_id)
    if report:
        report.upvotes += 1
        await db.commit()
        return True
    return False


# ── Known Scam Entities ────────────────────────────────────────
async def lookup_entity(db: AsyncSession, entity_type: str, value: str) -> KnownScamEntity | None:
    r = await db.execute(
        select(KnownScamEntity)
        .where(and_(KnownScamEntity.entity_type == entity_type,
                    KnownScamEntity.entity_value == value.lower()))
    )
    return r.scalar_one_or_none()

async def upsert_entity(db: AsyncSession, entity_type: str, value: str,
                        scam_type: str, risk_score: int = 80) -> KnownScamEntity:
    entity = await lookup_entity(db, entity_type, value)
    if entity:
        entity.report_count += 1
        entity.risk_score = min(entity.risk_score + 5, 100)
        entity.updated_at = datetime.now(timezone.utc)
    else:
        entity = KnownScamEntity(
            entity_type=entity_type, entity_value=value.lower(),
            scam_type=scam_type, risk_score=risk_score
        )
        db.add(entity)
    await db.commit()
    return entity

async def bulk_lookup(db: AsyncSession, phones: list, upi_ids: list,
                      domains: list) -> dict:
    hits = []
    total_reports = 0

    for phone in phones:
        e = await lookup_entity(db, "phone", phone)
        if e:
            hits.append(f"Phone {phone}: {e.report_count} reports ({e.scam_type})")
            total_reports += e.report_count

    for upi in upi_ids:
        e = await lookup_entity(db, "upi", upi)
        if e:
            hits.append(f"UPI {upi}: {e.report_count} reports ({e.scam_type})")
            total_reports += e.report_count

    for domain in domains:
        e = await lookup_entity(db, "domain", domain)
        if e:
            hits.append(f"Domain {domain}: {e.report_count} reports ({e.scam_type})")
            total_reports += e.report_count

    return {"prior_reports": total_reports, "hits": hits}


# ── Newsletter ─────────────────────────────────────────────────
async def subscribe_newsletter(db: AsyncSession, email: str) -> bool:
    existing = await db.scalar(select(NewsletterSubscriber).where(NewsletterSubscriber.email == email))
    if existing:
        existing.is_active = True
        await db.commit()
        return False
    db.add(NewsletterSubscriber(email=email))
    await db.commit()
    return True


# ── Contact ────────────────────────────────────────────────────
async def save_contact(db: AsyncSession, name: str, email: str,
                       subject: str, message: str) -> ContactMessage:
    msg = ContactMessage(name=name, email=email, subject=subject, message=message)
    db.add(msg)
    await db.commit()
    return msg


# ── Bookmarks ──────────────────────────────────────────────────
async def add_bookmark(db: AsyncSession, user_id: str, scan_id: int, note: str = "") -> Bookmark:
    bm = Bookmark(user_id=user_id, scan_id=scan_id, note=note)
    db.add(bm)
    await db.commit()
    return bm

async def get_bookmarks(db: AsyncSession, user_id: str) -> list[Bookmark]:
    r = await db.execute(
        select(Bookmark).where(Bookmark.user_id == user_id)
        .order_by(desc(Bookmark.created_at))
    )
    return r.scalars().all()
