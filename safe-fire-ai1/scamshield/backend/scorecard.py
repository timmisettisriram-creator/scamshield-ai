from schemas import RiskFactor, SafetyScorecard


def build_scorecard(nlp: dict, infra: dict, graph: dict,
                    email_intel: dict = None, url_rep: dict = None,
                    pattern: dict = None) -> SafetyScorecard:

    factors = []
    category_scores = {
        "content":  [],
        "email":    [],
        "url":      [],
        "salary":   [],
        "network":  [],
        "behavior": [],
    }

    # ── Content / NLP ──────────────────────────────────────────
    if nlp.get("urgency_score", 0) > 0:
        s = nlp["urgency_score"]
        factors.append(RiskFactor(
            label="Urgency Language", score=s,
            severity="high" if s > 55 else "medium",
            explanation="Artificial time pressure stops you from verifying the offer.",
            icon="⏰", category="content"
        ))
        category_scores["content"].append(s)

    if nlp.get("behavioral_score", 0) > 0:
        s = nlp["behavioral_score"]
        factors.append(RiskFactor(
            label="Psychological Manipulation", score=s,
            severity="high" if s > 50 else "medium",
            explanation="Phrases like 'you've been selected' or 'dream job' are emotional manipulation tactics.",
            icon="🧠", category="behavior"
        ))
        category_scores["behavior"].append(s)

    if nlp.get("salary_bait"):
        factors.append(RiskFactor(
            label="Unrealistic Salary Claim", score=82,
            severity="high",
            explanation="₹5,000–10,000/day for simple tasks is 6–10x market rate — a classic scam signal.",
            icon="💰", category="salary"
        ))
        category_scores["salary"].append(82)

    if nlp.get("fee_request"):
        factors.append(RiskFactor(
            label="Upfront Fee Requested", score=95,
            severity="high",
            explanation="Legitimate employers NEVER ask you to pay to get a job. This is the #1 scam signal.",
            icon="🚫", category="content"
        ))
        category_scores["content"].append(95)

    if nlp.get("telegram_task"):
        factors.append(RiskFactor(
            label="Telegram Task Scam Pattern", score=88,
            severity="high",
            explanation="'Like & Earn' Telegram tasks are a widespread Indian scam. No legitimate job works this way.",
            icon="📱", category="content"
        ))
        category_scores["content"].append(88)

    if nlp.get("phishing"):
        factors.append(RiskFactor(
            label="Phishing / Data Harvesting", score=90,
            severity="high",
            explanation="Requests for OTP, Aadhaar, PAN, or bank details via chat are phishing attempts.",
            icon="🎣", category="content"
        ))
        category_scores["content"].append(90)

    if nlp.get("fake_recruiter"):
        factors.append(RiskFactor(
            label="Fake Recruiter Pattern", score=65,
            severity="medium",
            explanation="Language mimics legitimate recruiters but combined with other signals suggests fraud.",
            icon="👤", category="behavior"
        ))
        category_scores["behavior"].append(65)

    if nlp.get("impersonated_brands"):
        brands = ", ".join(nlp["impersonated_brands"])
        factors.append(RiskFactor(
            label="Brand Impersonation", score=85,
            severity="high",
            explanation=f"Message mentions '{brands}' — scammers impersonate trusted companies to gain trust.",
            icon="🏢", category="behavior"
        ))
        category_scores["behavior"].append(85)

    if nlp.get("hinglish_scam"):
        factors.append(RiskFactor(
            label="Regional Scam Language Pattern", score=55,
            severity="medium",
            explanation="Common Hinglish/Hindi/Telugu phrases used in Indian WFH scams detected.",
            icon="🗣️", category="content"
        ))
        category_scores["content"].append(55)

    # ── Email Intelligence ─────────────────────────────────────
    if email_intel and email_intel.get("risk_score", 0) > 0:
        s = email_intel["risk_score"]
        flags_text = "; ".join(email_intel.get("flags", [])[:2])
        factors.append(RiskFactor(
            label="Suspicious Email Domain", score=s,
            severity="high" if s > 60 else "medium",
            explanation=flags_text or "Email domain raises red flags.",
            icon="📧", category="email"
        ))
        category_scores["email"].append(s)

    # ── URL Reputation ─────────────────────────────────────────
    if url_rep and url_rep.get("risk_score", 0) > 0:
        s = url_rep["risk_score"]
        flags_text = "; ".join(url_rep.get("flags", [])[:2])
        factors.append(RiskFactor(
            label="Suspicious URL / Link", score=s,
            severity="high" if s > 60 else "medium",
            explanation=flags_text or "URL shows signs of being a scam or phishing site.",
            icon="🔗", category="url"
        ))
        category_scores["url"].append(s)

    # ── Infrastructure ─────────────────────────────────────────
    if infra and infra.get("risk_score", 0) > 0:
        s = infra["risk_score"]
        age = infra.get("domain_age_days")
        age_text = f"{age} days old" if age is not None else "unknown age"
        notes = "; ".join(infra.get("notes", [])[:2])
        factors.append(RiskFactor(
            label="Suspicious Domain / Website", score=min(s, 95),
            severity="high" if s > 50 else "medium",
            explanation=f"Domain is {age_text}. {notes}",
            icon="🌐", category="url"
        ))
        category_scores["url"].append(s)

    # ── Trust Graph ────────────────────────────────────────────
    if graph and graph.get("prior_reports", 0) > 0:
        s = min(graph["prior_reports"] * 2, 100)
        hits_text = "; ".join(graph.get("hits", [])[:2])
        factors.append(RiskFactor(
            label="Known Scam Network Match", score=s,
            severity="high",
            explanation=f"Entities match {graph['prior_reports']} prior fraud reports. {hits_text}",
            icon="🕸️", category="network"
        ))
        category_scores["network"].append(s)

    # ── Pattern Learning ───────────────────────────────────────
    if pattern and pattern.get("bonus", 0) > 0:
        hits_text = "; ".join(pattern.get("hits", [])[:2])
        factors.append(RiskFactor(
            label="Repeated Scam Pattern", score=min(pattern["bonus"] + 40, 90),
            severity="high",
            explanation=f"This message matches patterns seen before: {hits_text}",
            icon="🔁", category="network"
        ))
        category_scores["network"].append(pattern["bonus"] + 40)

    # ── Compute overall ────────────────────────────────────────
    all_scores = [s for scores in category_scores.values() for s in scores]
    if all_scores:
        overall = int(sum(all_scores) / len(all_scores))
        high_count = sum(1 for s in all_scores if s >= 80)
        if high_count >= 2:
            overall = min(overall + 15, 100)
    else:
        overall = 5

    overall = min(overall, 100)
    verdict = "SCAM" if overall >= 70 else "SUSPICIOUS" if overall >= 35 else "SAFE"

    # Build category summary for charts
    cat_summary = {}
    for cat, scores in category_scores.items():
        cat_summary[cat] = int(sum(scores) / len(scores)) if scores else 0

    advice_map = {
        "SCAM": "Do NOT proceed. Block the sender and report at cybercrime.gov.in (Helpline: 1930).",
        "SUSPICIOUS": "Verify independently — call the company's official number. Never pay upfront or share OTP/documents.",
        "SAFE": "Looks relatively safe, but always verify before sharing personal documents or paying anything.",
    }

    return SafetyScorecard(
        overall_risk=overall,
        verdict=verdict,
        factors=factors,
        advice=advice_map[verdict],
        category_scores=cat_summary,
        language=nlp.get("language", "english"),
    )
