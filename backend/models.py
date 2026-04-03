"""
All database models.
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    Text, ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship
from database import Base


def now_utc():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id            = Column(String, primary_key=True)
    email         = Column(String, unique=True, nullable=True, index=True)
    phone         = Column(String, unique=True, nullable=True, index=True)
    name          = Column(String, nullable=True)
    avatar        = Column(String, nullable=True)
    provider      = Column(String, default="phone")   # google | phone
    is_verified   = Column(Boolean, default=False)
    is_admin      = Column(Boolean, default=False)
    is_banned     = Column(Boolean, default=False)
    safety_score  = Column(Integer, default=100)
    total_scans   = Column(Integer, default=0)
    scams_caught  = Column(Integer, default=0)
    created_at    = Column(DateTime(timezone=True), default=now_utc)
    last_login    = Column(DateTime(timezone=True), default=now_utc)

    scans    = relationship("ScanRecord",   back_populates="user", cascade="all, delete")
    reports  = relationship("ScamReport",   back_populates="reporter", cascade="all, delete")
    bookmarks = relationship("Bookmark",    back_populates="user", cascade="all, delete")
    alerts   = relationship("AlertSetting", back_populates="user", cascade="all, delete")


class ScanRecord(Base):
    __tablename__ = "scan_records"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_id       = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    input_text    = Column(Text, nullable=True)
    input_domain  = Column(String, nullable=True)
    verdict       = Column(String, index=True)
    risk_score    = Column(Integer)
    category_scores = Column(JSON, default={})
    factors       = Column(JSON, default=[])
    language      = Column(String, default="english")
    phones_found  = Column(JSON, default=[])
    upi_found     = Column(JSON, default=[])
    urls_found    = Column(JSON, default=[])
    emails_found  = Column(JSON, default=[])
    ip_address    = Column(String, nullable=True)
    created_at    = Column(DateTime(timezone=True), default=now_utc, index=True)

    user = relationship("User", back_populates="scans")

    __table_args__ = (
        Index("ix_scan_verdict_date", "verdict", "created_at"),
    )


class ScamReport(Base):
    __tablename__ = "scam_reports"
    id            = Column(Integer, primary_key=True, autoincrement=True)
    reporter_id   = Column(String, ForeignKey("users.id"), nullable=True)
    scam_type     = Column(String, index=True)
    snippet       = Column(Text)
    full_text     = Column(Text, nullable=True)
    location      = Column(String, default="India")
    state         = Column(String, nullable=True)
    risk_score    = Column(Integer)
    verdict       = Column(String)
    upvotes       = Column(Integer, default=0)
    is_verified   = Column(Boolean, default=False)
    is_flagged    = Column(Boolean, default=False)
    phones        = Column(JSON, default=[])
    upi_ids       = Column(JSON, default=[])
    domains       = Column(JSON, default=[])
    created_at    = Column(DateTime(timezone=True), default=now_utc, index=True)

    reporter = relationship("User", back_populates="reports")
    upvote_records = relationship("ReportUpvote", back_populates="report", cascade="all, delete")


class ReportUpvote(Base):
    __tablename__ = "report_upvotes"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    report_id  = Column(Integer, ForeignKey("scam_reports.id"), index=True)
    user_id    = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    report = relationship("ScamReport", back_populates="upvote_records")


class KnownScamEntity(Base):
    __tablename__ = "known_scam_entities"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    entity_type  = Column(String, index=True)   # phone | upi | domain | email | company
    entity_value = Column(String, index=True)
    scam_type    = Column(String)
    report_count = Column(Integer, default=1)
    risk_score   = Column(Integer, default=80)
    is_verified  = Column(Boolean, default=False)
    source       = Column(String, default="community")  # community | cybercrime.gov | manual
    added_at     = Column(DateTime(timezone=True), default=now_utc)
    updated_at   = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    __table_args__ = (
        Index("ix_entity_type_value", "entity_type", "entity_value"),
    )


class Bookmark(Base):
    __tablename__ = "bookmarks"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(String, ForeignKey("users.id"), index=True)
    scan_id    = Column(Integer, ForeignKey("scan_records.id"))
    note       = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    user = relationship("User", back_populates="bookmarks")


class AlertSetting(Base):
    __tablename__ = "alert_settings"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    user_id         = Column(String, ForeignKey("users.id"), index=True)
    email_alerts    = Column(Boolean, default=True)
    sms_alerts      = Column(Boolean, default=False)
    new_scam_type   = Column(Boolean, default=True)
    weekly_digest   = Column(Boolean, default=True)
    created_at      = Column(DateTime(timezone=True), default=now_utc)

    user = relationship("User", back_populates="alerts")


class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    email      = Column(String, unique=True, index=True)
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)


class ContactMessage(Base):
    __tablename__ = "contact_messages"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    name       = Column(String)
    email      = Column(String)
    subject    = Column(String)
    message    = Column(Text)
    is_read    = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)


class ScamTrend(Base):
    __tablename__ = "scam_trends"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    date       = Column(String, index=True)   # YYYY-MM-DD
    scam_type  = Column(String)
    count      = Column(Integer, default=0)
    avg_risk   = Column(Float, default=0)
    state      = Column(String, nullable=True)
