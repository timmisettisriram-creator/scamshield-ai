"""
Seed the database with known scam entities from Indian cybercrime data.
Run once: python seed_db.py
"""
import asyncio
from database import init_db, AsyncSessionLocal
from models import KnownScamEntity
from sqlalchemy import select

SEED_ENTITIES = [
    # Phones
    ("phone", "9876543210", "Telegram Task Scam", 90),
    ("phone", "8765432109", "Fake Job Offer", 85),
    ("phone", "7654321098", "UPI Fraud", 95),
    ("phone", "9988776655", "Work From Home Scam", 80),
    ("phone", "9123456789", "Fake Recruiter", 82),
    ("phone", "8899001122", "Phishing", 88),
    # UPI IDs
    ("upi", "earn.daily@paytm",   "Task Scam", 92),
    ("upi", "jobs.india@ybl",     "Fake Recruiter", 85),
    ("upi", "workfromhome@upi",   "WFH Fraud", 88),
    ("upi", "taskpay99@okaxis",   "Telegram Task Scam", 96),
    ("upi", "quickearn@paytm",    "Task Scam", 90),
    ("upi", "dailypay@ybl",       "Salary Bait", 87),
    ("upi", "hiringnow@okicici",  "Fake Job", 84),
    # Domains
    ("domain", "quickjobs-india.com",   "Fake Job Portal", 91),
    ("domain", "earnmoney-daily.in",    "Task Scam", 95),
    ("domain", "hiringnow-india.com",   "Fake Recruiter", 88),
    ("domain", "workfromhome-earn.in",  "WFH Fraud", 90),
    ("domain", "telegram-tasks.co.in",  "Telegram Task Scam", 97),
    ("domain", "amazon-task-team.com",  "Brand Impersonation", 96),
    ("domain", "google-wfh-india.com",  "Brand Impersonation", 95),
    ("domain", "flipkart-hiring.in",    "Brand Impersonation", 93),
    ("domain", "tcs-recruitment.co",    "Fake Recruiter", 89),
    ("domain", "infosys-jobs.xyz",      "Fake Recruiter", 91),
    ("domain", "daily-task-earn.com",   "Task Scam", 94),
    ("domain", "part-time-jobs.tk",     "WFH Fraud", 92),
    # Emails
    ("email", "amazon.hiring2024@gmail.com",  "Brand Impersonation", 90),
    ("email", "google.wfh.india@gmail.com",   "Brand Impersonation", 92),
    ("email", "tcs.recruitment@yahoo.com",    "Fake Recruiter", 88),
    ("email", "infosys.hr.cell@gmail.com",    "Fake Recruiter", 86),
    # Companies (impersonated)
    ("company", "amazon task team",      "Brand Impersonation", 95),
    ("company", "flipkart hiring cell",  "Brand Impersonation", 93),
    ("company", "google work from home", "Brand Impersonation", 96),
    ("company", "tcs recruitment cell",  "Fake Recruiter", 88),
    ("company", "infosys task force",    "Fake Recruiter", 86),
    ("company", "swiggy delivery task",  "Brand Impersonation", 89),
    ("company", "zomato part time",      "Brand Impersonation", 87),
]


async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        for entity_type, value, scam_type, risk in SEED_ENTITIES:
            existing = await db.scalar(
                select(KnownScamEntity).where(
                    KnownScamEntity.entity_type == entity_type,
                    KnownScamEntity.entity_value == value.lower()
                )
            )
            if not existing:
                db.add(KnownScamEntity(
                    entity_type=entity_type,
                    entity_value=value.lower(),
                    scam_type=scam_type,
                    risk_score=risk,
                    report_count=max(1, risk - 60),
                    is_verified=True,
                    source="seed",
                ))
        await db.commit()
        print(f"Seeded {len(SEED_ENTITIES)} known scam entities.")


if __name__ == "__main__":
    asyncio.run(seed())
