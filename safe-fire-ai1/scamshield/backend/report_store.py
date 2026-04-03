"""
In-memory community report store (replace with DB in production).
"""
from datetime import datetime
from typing import List
import threading

_lock = threading.Lock()

_reports: List[dict] = [
    {
        "id": 1,
        "type": "Telegram Task Scam",
        "snippet": "Earn ₹8,000/day liking YouTube videos. Pay ₹500 to join.",
        "location": "Mumbai",
        "risk": 96,
        "verdict": "SCAM",
        "time": "2 hours ago",
        "upvotes": 34,
    },
    {
        "id": 2,
        "type": "Fake Job Portal",
        "snippet": "Amazon Task Team hiring — work from home, ₹10,000/day.",
        "location": "Delhi",
        "risk": 91,
        "verdict": "SCAM",
        "time": "5 hours ago",
        "upvotes": 21,
    },
    {
        "id": 3,
        "type": "Phishing / Data Harvest",
        "snippet": "Infosys Task Force — share OTP and Aadhaar to confirm joining.",
        "location": "Bengaluru",
        "risk": 88,
        "verdict": "SCAM",
        "time": "1 day ago",
        "upvotes": 47,
    },
    {
        "id": 4,
        "type": "UPI Fraud",
        "snippet": "Registration fee ₹1,000 refundable — send to taskpay99@okaxis.",
        "location": "Hyderabad",
        "risk": 94,
        "verdict": "SCAM",
        "time": "1 day ago",
        "upvotes": 29,
    },
    {
        "id": 5,
        "type": "Fake Recruiter",
        "snippet": "TCS Recruitment Cell — pay ₹2,000 training fee before joining.",
        "location": "Pune",
        "risk": 85,
        "verdict": "SCAM",
        "time": "2 days ago",
        "upvotes": 18,
    },
]

_next_id = 6


def get_recent_reports(limit: int = 10) -> List[dict]:
    with _lock:
        return list(reversed(_reports[-limit:]))


def add_report(report_type: str, snippet: str, location: str, risk: int, verdict: str) -> dict:
    global _next_id
    with _lock:
        entry = {
            "id": _next_id,
            "type": report_type,
            "snippet": snippet[:120],
            "location": location or "India",
            "risk": risk,
            "verdict": verdict,
            "time": "Just now",
            "upvotes": 0,
        }
        _reports.append(entry)
        _next_id += 1
        return entry


def upvote_report(report_id: int) -> bool:
    with _lock:
        for r in _reports:
            if r["id"] == report_id:
                r["upvotes"] += 1
                return True
    return False
