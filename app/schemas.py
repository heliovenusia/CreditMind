from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class IngestRequest(BaseModel):
    aa_payload: Optional[Dict[str, Any]] = None
    sms_dump: Optional[Dict[str, Any]] = None
    telecom_meta: Optional[Dict[str, Any]] = None

class IngestResponse(BaseModel):
    ingestion_id: str

class RunRequest(BaseModel):
    ingestion_id: str

class ScoreResponse(BaseModel):
    score: float
    decision: str
    reason_codes: List[str]
    shap_summary: Dict[str, float]
    coach_tips: List[str]

class AuditResponse(BaseModel):
    consent: Dict[str, Any]
    stored: List[str]
    created_at: str