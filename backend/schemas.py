from pydantic import BaseModel
from typing import Optional, List, Dict

class AnalysisRequest(BaseModel):
    text: Optional[str] = None
    domain: Optional[str] = None
    image_base64: Optional[str] = None

class RiskFactor(BaseModel):
    label: str
    score: int
    severity: str
    explanation: str
    icon: str
    category: str = "content"

class SafetyScorecard(BaseModel):
    overall_risk: int
    verdict: str
    factors: List[RiskFactor]
    advice: str
    category_scores: Dict[str, int] = {}
    language: str = "english"
    report_url: str = "https://cybercrime.gov.in"
