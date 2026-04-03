"""
In-memory Trust Graph (simulates Neo4j for hackathon demo).
Seeded with real-pattern scam entities from Indian cybercrime reports.
"""

SCAM_SEED_DB = {
    "phones": {
        "9876543210": {"reports": 12, "type": "Telegram Task Scam"},
        "8765432109": {"reports": 7,  "type": "Fake Job Offer"},
        "7654321098": {"reports": 19, "type": "UPI Fraud"},
        "9988776655": {"reports": 4,  "type": "Work From Home Scam"},
    },
    "upi_ids": {
        "earn.daily@paytm":    {"reports": 23, "type": "Task Scam"},
        "jobs.india@ybl":      {"reports": 8,  "type": "Fake Recruiter"},
        "workfromhome@upi":    {"reports": 15, "type": "WFH Fraud"},
        "taskpay99@okaxis":    {"reports": 31, "type": "Telegram Task Scam"},
    },
    "domains": {
        "quickjobs-india.com":   {"reports": 44, "type": "Fake Job Portal"},
        "earnmoney-daily.in":    {"reports": 67, "type": "Task Scam"},
        "hiringnow-india.com":   {"reports": 12, "type": "Fake Recruiter"},
        "workfromhome-earn.in":  {"reports": 29, "type": "WFH Fraud"},
        "telegram-tasks.co.in":  {"reports": 88, "type": "Telegram Task Scam"},
    },
    "company_names": {
        "amazon task team":      {"reports": 156, "type": "Brand Impersonation"},
        "flipkart hiring cell":  {"reports": 89,  "type": "Brand Impersonation"},
        "google work from home": {"reports": 201, "type": "Brand Impersonation"},
        "tcs recruitment cell":  {"reports": 43,  "type": "Fake Recruiter"},
        "infosys task force":    {"reports": 37,  "type": "Fake Recruiter"},
    },
}


def query_graph(phones: list, upi_ids: list, urls: list, text: str) -> dict:
    hits = []
    total_reports = 0

    for phone in phones:
        clean = phone.replace("+91", "").replace(" ", "")
        if clean in SCAM_SEED_DB["phones"]:
            entry = SCAM_SEED_DB["phones"][clean]
            hits.append(f"Phone {clean}: {entry['reports']} reports ({entry['type']})")
            total_reports += entry["reports"]

    for upi in upi_ids:
        if upi.lower() in SCAM_SEED_DB["upi_ids"]:
            entry = SCAM_SEED_DB["upi_ids"][upi.lower()]
            hits.append(f"UPI {upi}: {entry['reports']} reports ({entry['type']})")
            total_reports += entry["reports"]

    for url in urls:
        for domain, entry in SCAM_SEED_DB["domains"].items():
            if domain in url.lower():
                hits.append(f"Domain {domain}: {entry['reports']} reports ({entry['type']})")
                total_reports += entry["reports"]

    text_lower = text.lower() if text else ""
    for company, entry in SCAM_SEED_DB["company_names"].items():
        if company in text_lower:
            hits.append(f"Company '{company}': {entry['reports']} reports ({entry['type']})")
            total_reports += entry["reports"]

    return {
        "prior_reports": total_reports,
        "hits": hits,
    }
