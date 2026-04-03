"""Seed Firestore with known scam entities."""
import asyncio
from firebase_config import init_firebase, get_firestore

SEED_ENTITIES = [
    ("phone", "9876543210", "Telegram Task Scam", 90),
    ("phone", "8765432109", "Fake Job Offer", 85),
    ("phone", "7654321098", "UPI Fraud", 95),
    ("phone", "9988776655", "Work From Home Scam", 80),
    ("upi", "earn.daily@paytm",   "Task Scam", 92),
    ("upi", "jobs.india@ybl",     "Fake Recruiter", 85),
    ("upi", "taskpay99@okaxis",   "Telegram Task Scam", 96),
    ("upi", "quickearn@paytm",    "Task Scam", 90),
    ("domain", "quickjobs-india.com",   "Fake Job Portal", 91),
    ("domain", "earnmoney-daily.in",    "Task Scam", 95),
    ("domain", "hiringnow-india.com",   "Fake Recruiter", 88),
    ("domain", "workfromhome-earn.in",  "WFH Fraud", 90),
    ("domain", "telegram-tasks.co.in",  "Telegram Task Scam", 97),
    ("domain", "amazon-task-team.com",  "Brand Impersonation", 96),
    ("domain", "google-wfh-india.com",  "Brand Impersonation", 95),
    ("company", "amazon task team",      "Brand Impersonation", 95),
    ("company", "google work from home", "Brand Impersonation", 96),
    ("company", "tcs recruitment cell",  "Fake Recruiter", 88),
]


async def seed():
    init_firebase()
    fs = get_firestore()
    collection = fs.collection("known_entities")
    seeded = 0
    for entity_type, value, scam_type, risk in SEED_ENTITIES:
        # Check if already exists
        docs = collection.where("entity_type", "==", entity_type).where("entity_value", "==", value.lower()).limit(1)
        existing = [d async for d in docs.stream()]
        if not existing:
            from datetime import datetime, timezone
            await collection.add({
                "entity_type": entity_type,
                "entity_value": value.lower(),
                "scam_type": scam_type,
                "risk_score": risk,
                "report_count": max(1, risk - 60),
                "is_verified": True,
                "source": "seed",
                "added_at": datetime.now(timezone.utc),
            })
            seeded += 1
    if seeded:
        print(f"Seeded {seeded} entities to Firestore.")


if __name__ == "__main__":
    asyncio.run(seed())
