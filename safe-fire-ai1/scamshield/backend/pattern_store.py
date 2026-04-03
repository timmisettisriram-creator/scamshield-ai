"""
Smart Scam Pattern Learning — stores past analyses, detects repeated patterns.
In-memory for hackathon; swap list for SQLite/Redis in production.
"""
import hashlib, time, threading
from collections import defaultdict
from typing import List

_lock = threading.Lock()

# Raw history: list of {hash, text_snippet, verdict, risk, ts, signals}
_history: List[dict] = []

# Pattern frequency maps
_email_freq:  dict[str, int] = defaultdict(int)
_phone_freq:  dict[str, int] = defaultdict(int)
_upi_freq:    dict[str, int] = defaultdict(int)
_domain_freq: dict[str, int] = defaultdict(int)
_text_hashes: dict[str, int] = defaultdict(int)   # near-duplicate detection


def _fingerprint(text: str) -> str:
    """Normalize + hash for near-duplicate detection."""
    normalized = " ".join(text.lower().split())
    return hashlib.md5(normalized.encode()).hexdigest()


def record_analysis(text: str, verdict: str, risk: int,
                    phones: list, upi_ids: list, urls: list, domains: list):
    fp = _fingerprint(text)
    with _lock:
        _text_hashes[fp] += 1
        for p in phones:   _phone_freq[p]  += 1
        for u in upi_ids:  _upi_freq[u]    += 1
        for d in domains:  _domain_freq[d] += 1
        _history.append({
            "hash": fp,
            "snippet": text[:120],
            "verdict": verdict,
            "risk": risk,
            "ts": time.time(),
        })
        # Keep last 500
        if len(_history) > 500:
            _history.pop(0)


def get_repeat_score(text: str, phones: list, upi_ids: list, domains: list) -> dict:
    """Return extra risk score if entities have been seen before."""
    fp = _fingerprint(text)
    hits = []
    bonus = 0

    with _lock:
        if _text_hashes.get(fp, 0) > 0:
            hits.append(f"Identical message seen {_text_hashes[fp]} time(s) before")
            bonus += min(_text_hashes[fp] * 15, 60)

        for p in phones:
            c = _phone_freq.get(p, 0)
            if c:
                hits.append(f"Phone {p} appeared in {c} prior scan(s)")
                bonus += min(c * 10, 50)

        for u in upi_ids:
            c = _upi_freq.get(u, 0)
            if c:
                hits.append(f"UPI {u} appeared in {c} prior scan(s)")
                bonus += min(c * 10, 50)

        for d in domains:
            c = _domain_freq.get(d, 0)
            if c:
                hits.append(f"Domain {d} appeared in {c} prior scan(s)")
                bonus += min(c * 10, 50)

    return {"bonus": min(bonus, 40), "hits": hits}


def get_stats() -> dict:
    with _lock:
        total = len(_history)
        scams = sum(1 for h in _history if h["verdict"] == "SCAM")
        return {
            "total_scanned": total,
            "scams_detected": scams,
            "unique_phones_flagged": len(_phone_freq),
            "unique_upi_flagged": len(_upi_freq),
            "unique_domains_flagged": len(_domain_freq),
        }
