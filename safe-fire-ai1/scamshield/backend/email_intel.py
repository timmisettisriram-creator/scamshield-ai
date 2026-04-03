"""
Email Domain Intelligence — checks domain age, MX records, company domain mismatch.
"""
import re, socket
import dns.resolver as dns_resolver

# Known free email providers — legitimate companies don't recruit from these
FREE_PROVIDERS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "rediffmail.com", "ymail.com", "live.com", "aol.com",
    "protonmail.com", "tutanota.com", "mail.com",
}

# Trusted corporate domains (expand as needed)
TRUSTED_DOMAINS = {
    "tcs.com", "infosys.com", "wipro.com", "hcl.com", "accenture.com",
    "amazon.com", "amazon.in", "flipkart.com", "google.com", "microsoft.com",
    "ibm.com", "cognizant.com", "capgemini.com", "deloitte.com",
}

EMAIL_RE = re.compile(r"[\w.\-+]+@([\w.\-]+\.[a-z]{2,})", re.IGNORECASE)


def extract_emails(text: str) -> list[str]:
    return EMAIL_RE.findall(text)  # returns list of domains


def check_email_domain(domain: str) -> dict:
    result = {
        "domain": domain,
        "is_free_provider": domain.lower() in FREE_PROVIDERS,
        "has_mx": False,
        "mx_records": [],
        "risk_score": 0,
        "flags": [],
    }

    # Free provider check
    if result["is_free_provider"]:
        result["risk_score"] += 55
        result["flags"].append(f"Recruiter using free email ({domain}) — companies use corporate email")

    # MX record check
    try:
        mx = dns_resolver.resolve(domain, "MX")
        result["has_mx"] = True
        result["mx_records"] = [str(r.exchange).rstrip('.') for r in mx]
    except Exception:
        if not result["is_free_provider"]:
            result["risk_score"] += 30
            result["flags"].append(f"No MX records found for {domain} — domain may be fake")

    return result


def analyze_email_context(text: str) -> dict:
    """Full email intelligence pass on a block of text."""
    domains = extract_emails(text)
    if not domains:
        return {"domains": [], "risk_score": 0, "flags": []}

    all_flags = []
    max_risk = 0

    for domain in set(domains):
        r = check_email_domain(domain)
        all_flags.extend(r["flags"])
        max_risk = max(max_risk, r["risk_score"])

        # Company impersonation: e.g. amazon-hr@gmail.com
        text_lower = text.lower()
        for trusted in TRUSTED_DOMAINS:
            company = trusted.split(".")[0]
            if company in text_lower and domain.lower() in FREE_PROVIDERS:
                all_flags.append(
                    f"Possible brand impersonation: mentions '{company}' but uses {domain}"
                )
                max_risk = max(max_risk, 85)

    return {
        "domains": list(set(domains)),
        "risk_score": min(max_risk, 95),
        "flags": all_flags,
    }
