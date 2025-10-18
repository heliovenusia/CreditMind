import os, json, uuid, joblib
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, UploadFile, File, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import numpy as np

from .schemas import IngestResponse, RunRequest, ScoreResponse, AuditResponse
from .feature_engineering import assemble_features
from . import model as mdl

BASE_DIR = os.getenv("CREDITMIND_BASE", "/mnt/data/creditmind_backend")
STORAGE = os.path.join(BASE_DIR, "storage")
MODELS = os.path.join(BASE_DIR, "models")
os.makedirs(STORAGE, exist_ok=True)
os.makedirs(MODELS, exist_ok=True)

MODEL_PATH = os.path.join(MODELS, "baseline.pkl")
FEATURES_PATH = os.path.join(MODELS, "features.json")

app = FastAPI(title="CreditMind API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _ingest_dir(ing_id: str) -> str:
    d = os.path.join(STORAGE, ing_id)
    os.makedirs(d, exist_ok=True)
    return d

@app.post("/score/ingest", response_model=IngestResponse)
async def ingest(
    aa_payload: Optional[str] = Body(default=None),
    sms_dump: Optional[str] = Body(default=None),
    telecom_meta: Optional[str] = Body(default=None),
    bank_statement_csv: Optional[UploadFile] = File(default=None)
):
    ing_id = str(uuid.uuid4())
    d = _ingest_dir(ing_id)

    consent = {"created_at": datetime.utcnow().isoformat(), "sources": []}
    payloads: Dict[str, Any] = {}

    if aa_payload:
        try:
            payloads["aa_payload"] = json.loads(aa_payload)
            consent["sources"].append("aa_payload")
            (open(os.path.join(d, "aa_payload.json"), "w")).write(json.dumps(payloads["aa_payload"], indent=2))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid aa_payload JSON: {e}")

    if sms_dump:
        try:
            payloads["sms_dump"] = json.loads(sms_dump)
            consent["sources"].append("sms_dump")
            (open(os.path.join(d, "sms_dump.json"), "w")).write(json.dumps(payloads["sms_dump"], indent=2))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid sms_dump JSON: {e}")

    if telecom_meta:
        try:
            payloads["telecom_meta"] = json.loads(telecom_meta)
            consent["sources"].append("telecom_meta")
            (open(os.path.join(d, "telecom_meta.json"), "w")).write(json.dumps(payloads["telecom_meta"], indent=2))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid telecom_meta JSON: {e}")

    if bank_statement_csv is not None:
        content = await bank_statement_csv.read()
        with open(os.path.join(d, "bank_statement.csv"), "wb") as f:
            f.write(content)
        consent["sources"].append("bank_statement_csv")

    with open(os.path.join(d, "consent.json"), "w") as f:
        f.write(json.dumps(consent, indent=2))

    feats = assemble_features(payloads)
    with open(os.path.join(d, "features.json"), "w") as f:
        f.write(json.dumps(feats, indent=2))

    return {"ingestion_id": ing_id}

@app.post("/score/run", response_model=ScoreResponse)
async def run(req: RunRequest):
    d = _ingest_dir(req.ingestion_id)
    fpath = os.path.join(d, "features.json")
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Ingestion not found or features missing.")
    feats = json.loads(open(fpath).read())

    if not os.path.exists(MODEL_PATH):
        raise HTTPException(status_code=500, detail="Model not trained yet. Run training script.")
    pipe = joblib.load(MODEL_PATH)
    feature_list = json.loads(open(FEATURES_PATH).read())

    x = np.array([[feats.get(k, 0.0) for k in feature_list]], dtype=float)
    pd = float(pipe.predict_proba(x)[0,1])  # probability of default
    score = 1.0 - pd                        # approval score
    score = max(0.05, min(0.95, score))



    # SHAP approximation: use model coefficients if logistic regression
    try:
        coef = pipe.named_steps["model"].coef_[0]
        shap_vals = coef * pipe.named_steps["scaler"].transform(x)[0]
    except Exception:
        shap_vals = np.zeros(len(feature_list))

    reason_codes = mdl.top_reason_codes(feature_list, shap_vals, k=3)
    shap_summary = {feature_list[i]: float(shap_vals[i]) for i in range(len(feature_list))}
    decision = mdl.decide(score)

    tips = [mdl.COACH_TIPS.get(rc, "Improve behaviour indicated by reason code.") for rc in reason_codes]

    return {
        "score": round(score, 4),
        "decision": decision,
        "reason_codes": reason_codes,
        "shap_summary": shap_summary,
        "coach_tips": tips
    }

@app.get("/score/audit/{ingestion_id}", response_model=AuditResponse)
async def audit(ingestion_id: str):
    d = _ingest_dir(ingestion_id)
    cpath = os.path.join(d, "consent.json")
    if not os.path.exists(cpath):
        raise HTTPException(status_code=404, detail="Consent not found.")
    consent = json.loads(open(cpath).read())
    stored = [p for p in os.listdir(d) if p.endswith((".json",".csv"))]
    return {
        "consent": consent,
        "stored": stored,
        "created_at": consent.get("created_at","")
    }

@app.delete("/score/raw/{ingestion_id}")
async def purge_raw(ingestion_id: str):
    d = _ingest_dir(ingestion_id)
    for fn in ["aa_payload.json","sms_dump.json","telecom_meta.json","bank_statement.csv"]:
        f = os.path.join(d, fn)
        if os.path.exists(f):
            os.remove(f)
    return {"status": "ok", "message": "Raw artefacts deleted; derived features retained."}