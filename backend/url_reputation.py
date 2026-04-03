"""
URL Reputation — Google Safe Browsing + VirusTotal (API keys optional).
Falls back to heuristic checks when keys are not set.
"""
import os, re, hashlib, httpx
from urllib.parse import urlparse

GSB_API_KEY = os.getenv("GOOGLE_SAFE_BROWSING_KEY", "")
VT_API_KEY  = os.getenv("VIRUSTOTAL_KEY", "")

SUSPICIOUS_TLDS = {".tk", ".ml", ".ga", ".cf", ".gq", ".xyz", ".top", ".click", ".loan", ".work"}
SUSPICIOUS_KEYWORDS = [
    "earn", "task", "daily", "income", "job", "hire", "recruit",
    "work-from-home", "wfh", "money", "pay", "salary", "free",
]


def heuristic_url_check(url: str) -> dict:
    parsed = urlparse(url if url.startswith("http") else "http://" + url)
    domain = parsed.netloc.lower().replace("www.", "")
    path   = parsed.path.lower()
    risk   = 0
    flags  = []

    # Suspicious TLD
    for tld in SUSPICIOUS_TLDS:
        if domain.endswith(tld):
            risk += 40
            flags.append(f"Suspicious TLD: {tld}")

    # Keyword stuffing in domain
    kw_hits = [k for k in SUSPICIOUS_KEYWORDS if k in domain]
    if kw_hits:
        risk += min(len(kw_hits) * 15, 45)
        flags.append(f"Scam keywords in domain: {', '.join(kw_hits)}")

    # IP address as domain
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", domain):
        risk += 50
        flags.append("URL uses raw IP address instead of domain name")

    # Excessive subdomains
    if domain.count(".") >= 3:
        risk += 20
        flags.append("Excessive subdomains — common in phishing URLs")

    # Long random-looking path
    if len(path) > 60:
        risk += 15
        flags.append("Unusually long URL path")

    return {"url": url, "risk_score": min(risk, 95), "flags": flags, "source": "heuristic"}


async def check_google_safe_browsing(url: str) -> dict:
    if not GSB_API_KEY:
        return {}
    endpoint = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={GSB_API_KEY}"
    payload = {
        "client": {"clientId": "scamshield", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}],
        },
    }
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.post(endpoint, json=payload)
            data = r.json()
            if data.get("matches"):
                return {"flagged": True, "risk_score": 95, "source": "Google Safe Browsing",
                        "flags": [f"Google Safe Browsing: {m['threatType']}" for m in data["matches"]]}
    except Exception:
        pass
    return {"flagged": False, "risk_score": 0, "source": "Google Safe Browsing"}


async def check_virustotal(url: str) -> dict:
    if not VT_API_KEY:
        return {}
    url_id = hashlib.sha256(url.encode()).hexdigest()
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(
                f"https://www.virustotal.com/api/v3/urls/{url_id}",
                headers={"x-apikey": VT_API_KEY},
            )
            if r.status_code == 200:
                stats = r.json()["data"]["attributes"]["last_analysis_stats"]
                malicious = stats.get("malicious", 0)
                suspicious = stats.get("suspicious", 0)
                if malicious + suspicious > 0:
                    return {
                        "flagged": True,
                        "risk_score": min((malicious + suspicious) * 10, 95),
                        "source": "VirusTotal",
                        "flags": [f"VirusTotal: {malicious} malicious, {suspicious} suspicious engines"],
                    }
    except Exception:
        pass
    return {}


async def analyze_urls(urls: list[str]) -> dict:
    if not urls:
        return {"risk_score": 0, "flags": []}

    all_flags = []
    max_risk = 0

    for url in urls[:3]:  # check up to 3 URLs
        h = heuristic_url_check(url)
        all_flags.extend(h["flags"])
        max_risk = max(max_risk, h["risk_score"])

        gsb = await check_google_safe_browsing(url)
        if gsb.get("flagged"):
            all_flags.extend(gsb.get("flags", []))
            max_risk = max(max_risk, gsb.get("risk_score", 0))

        vt = await check_virustotal(url)
        if vt.get("flagged"):
            all_flags.extend(vt.get("flags", []))
            max_risk = max(max_risk, vt.get("risk_score", 0))

    return {"risk_score": min(max_risk, 95), "flags": all_flags}
