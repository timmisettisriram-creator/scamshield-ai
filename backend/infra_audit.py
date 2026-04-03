import whois
import ssl
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse


def extract_domain(text: str) -> str | None:
    """Pull domain from a URL string or plain domain."""
    if not text:
        return None
    if text.startswith("http"):
        parsed = urlparse(text)
        return parsed.netloc.replace("www.", "")
    return text.replace("www.", "").strip()


def audit_domain(domain: str) -> dict:
    result = {
        "domain": domain,
        "domain_age_days": None,
        "ssl_valid": False,
        "risk_score": 0,
        "notes": [],
    }

    # WHOIS age check
    try:
        w = whois.whois(domain)
        creation = w.creation_date
        if isinstance(creation, list):
            creation = creation[0]
        if creation:
            now = datetime.now(timezone.utc)
            if creation.tzinfo is None:
                creation = creation.replace(tzinfo=timezone.utc)
            age_days = (now - creation).days
            result["domain_age_days"] = age_days
            if age_days < 30:
                result["risk_score"] += 65
                result["notes"].append(f"Domain only {age_days} days old — very suspicious")
            elif age_days < 180:
                result["risk_score"] += 30
                result["notes"].append(f"Domain registered {age_days} days ago — relatively new")
    except Exception:
        result["risk_score"] += 35
        result["notes"].append("Could not verify domain registration — treat with caution")

    # SSL check
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=domain) as s:
            s.settimeout(5)
            s.connect((domain, 443))
            result["ssl_valid"] = True
    except Exception:
        result["risk_score"] += 25
        result["notes"].append("No valid SSL certificate found")

    return result
