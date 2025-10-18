# run this from *anywhere* (but while uvicorn is running)
import json, requests, pathlib

BASE = "http://127.0.0.1:8000"
DATA = pathlib.Path(r"D:\github\CreditMind\data")

aa  = json.loads((DATA/"aa_payload.json").read_text(encoding="utf-8"))
sms = json.loads((DATA/"sms_dump.json").read_text(encoding="utf-8"))
tel = json.loads((DATA/"telecom_meta.json").read_text(encoding="utf-8"))

# IMPORTANT: the API expects JSON STRINGS for these 3 fields
payload = {
    "aa_payload": json.dumps(aa),
    "sms_dump": json.dumps(sms),
    "telecom_meta": json.dumps(tel)
}

r = requests.post(f"{BASE}/score/ingest", json=payload, timeout=30)
print("INGEST:", r.status_code, r.text)
ingestion_id = r.json()["ingestion_id"]

r2 = requests.post(f"{BASE}/score/run", json={"ingestion_id": ingestion_id}, timeout=30)
print("RUN:", r2.status_code)
print(r2.json())  # <-- score, decision, reason_codes, tips
