import re

# ── Urgency / Psychological manipulation ──────────────────────
URGENCY_PATTERNS = [
    r"apply (now|immediately|today only|within \d+ hours?)",
    r"limited (seats?|slots?|openings?|positions?)",
    r"offer (expires?|ends?|closing)",
    r"don'?t miss",
    r"last (chance|opportunity|day|call)",
    r"urgent(ly)?",
    r"hurry",
    r"act (fast|now|quickly)",
    r"only \d+ (spots?|seats?|positions?) (left|remaining|available)",
    r"respond (within|in) \d+",
]

BEHAVIORAL_MANIPULATION = [
    r"you('ve| have) been (selected|chosen|shortlisted)",
    r"congratulations.{0,30}(selected|hired|chosen)",
    r"special (opportunity|offer|invitation)",
    r"exclusive (offer|opportunity|access)",
    r"you (qualify|are eligible|have been approved)",
    r"dream (job|opportunity|career)",
    r"life.?changing",
    r"financial (freedom|independence)",
    r"be your own boss",
    r"no (experience|qualification|degree) (needed|required)",
    r"work (from|at) (home|anywhere)",
    r"flexible (hours|timing|schedule)",
]

SALARY_BAIT_PATTERNS = [
    r"₹[\d,]+\s*(per|/)\s*(day|hour|task|week)",
    r"\d{4,}\s*rs?\s*(per|/)\s*(day|hour|task)",
    r"earn\s+₹?\d+",
    r"daily (earning|income|payment|payout)",
    r"\d+k?\s*(per|/)\s*day",
    r"upto?\s*₹?\s*\d+",
    r"guaranteed (income|earning|salary|payment)",
    r"passive income",
    r"earn (while|without) (you sleep|working|effort)",
]

FEE_PATTERNS = [
    r"registration fee",
    r"security deposit",
    r"training (fee|cost|charge)",
    r"pay (first|advance|upfront|before)",
    r"advance payment",
    r"refundable deposit",
    r"joining fee",
    r"processing fee",
    r"kit (fee|charge|cost)",
    r"material (fee|charge|cost)",
]

HINGLISH_SCAM_MARKERS = [
    "ghar baithe", "ghar se kaam", "part time kaam", "daily payment",
    "whatsapp karo", "join karo", "abhi apply", "paise kamao",
    "ghar baithe paise", "online kaam", "simple task", "aasaan kaam",
    "ghar par kaam", "khali time mein", "extra income",
]

HINDI_SCAM_MARKERS = [
    "घर बैठे", "पैसे कमाओ", "रोज़ कमाई", "आसान काम",
    "रजिस्ट्रेशन फीस", "अभी जुड़ें", "सीमित सीटें",
]

TELUGU_SCAM_MARKERS = [
    "ఇంటి నుండి", "సులభమైన పని", "రోజువారీ చెల్లింపు",
    "నమోదు రుసుము", "ఇప్పుడే చేరండి",
]

TELEGRAM_TASK_MARKERS = [
    "telegram task", "like and earn", "subscribe and earn",
    "youtube like", "follow karo", "task complete karo",
    "per task", "task based", "simple online task",
    "work from home task", "telegram group join",
    "channel subscribe", "video like task", "rating task",
]

PHISHING_MARKERS = [
    "verify your account", "click here to claim",
    "your account will be suspended", "confirm your details",
    "otp share", "share otp", "bank details required",
    "aadhar card send", "pan card send", "share your",
    "send your documents", "upload your id",
]

FAKE_RECRUITER_MARKERS = [
    "hr department", "recruitment cell", "hiring team",
    "talent acquisition", "placement cell",
    "we found your resume", "your profile matches",
    "shortlisted from naukri", "shortlisted from linkedin",
    "campus recruitment", "off campus drive",
]

# Trusted company names that scammers impersonate
IMPERSONATED_BRANDS = [
    "amazon", "flipkart", "google", "microsoft", "tcs", "infosys",
    "wipro", "accenture", "deloitte", "ibm", "cognizant", "capgemini",
    "hdfc", "icici", "sbi", "paytm", "phonepe", "swiggy", "zomato",
    "byju", "unacademy", "meesho", "myntra", "snapdeal",
]


def analyze_text(text: str) -> dict:
    if not text:
        return {}

    t = text.lower()

    urgency_hits = sum(1 for p in URGENCY_PATTERNS if re.search(p, t))
    behavioral_hits = sum(1 for p in BEHAVIORAL_MANIPULATION if re.search(p, t))
    salary_bait = any(re.search(p, t) for p in SALARY_BAIT_PATTERNS)
    fee_request = any(re.search(p, t) for p in FEE_PATTERNS)
    hinglish = any(m in t for m in HINGLISH_SCAM_MARKERS)
    hindi = any(m in text for m in HINDI_SCAM_MARKERS)
    telugu = any(m in text for m in TELUGU_SCAM_MARKERS)
    telegram_task = any(m in t for m in TELEGRAM_TASK_MARKERS)
    phishing = any(m in t for m in PHISHING_MARKERS)
    fake_recruiter = any(m in t for m in FAKE_RECRUITER_MARKERS)

    # Brand impersonation check
    impersonated = [b for b in IMPERSONATED_BRANDS if b in t]

    # Extract entities
    phones = re.findall(r"(?:\+91|0)?[6-9]\d{9}", text)
    upi_ids = re.findall(r"[\w.\-]+@[a-z]+", text)
    urls = re.findall(r"https?://[^\s]+|www\.[^\s]+", text)
    emails = re.findall(r"[\w.\-+]+@[\w.\-]+\.[a-z]{2,}", text)
    domains = list({u.split("/")[2].replace("www.", "") for u in urls if "://" in u})

    # Detect language
    lang = "english"
    if hindi:
        lang = "hindi"
    elif telugu:
        lang = "telugu"
    elif hinglish:
        lang = "hinglish"

    return {
        "urgency_score": min(urgency_hits * 25, 90),
        "behavioral_score": min(behavioral_hits * 20, 80),
        "salary_bait": salary_bait,
        "fee_request": fee_request,
        "hinglish_scam": hinglish or hindi or telugu,
        "telegram_task": telegram_task,
        "phishing": phishing,
        "fake_recruiter": fake_recruiter,
        "impersonated_brands": impersonated,
        "phones": phones,
        "upi_ids": upi_ids,
        "urls": urls,
        "emails": emails,
        "domains": domains,
        "language": lang,
    }
