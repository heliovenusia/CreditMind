# CreditMind Backend (FastAPI)

## Endpoints
- `POST /score/ingest` : Accept JSON strings (aa_payload, sms_dump, telecom_meta) and optional `bank_statement_csv` file.
- `POST /score/run` : Run scoring on an `ingestion_id`.
- `GET /score/audit/{ingestion_id}` : Inspect consent + stored artefacts.
- `DELETE /score/raw/{ingestion_id}` : Delete raw artefacts; keep derived features.

## Quickstart

```bash
pip install -r requirements.txt
python -m scripts.train_baseline
uvicorn app.main:app --reload --port 8000
```

### Example: Ingest + Run (using Python requests)
```python
import requests, json

url = "http://localhost:8000"

aa = json.load(open("../creditmind_demo/aa_payload.json"))
sms = json.load(open("../creditmind_demo/sms_dump.json"))
tel = json.load(open("../creditmind_demo/telecom_meta.json"))

resp = requests.post(f"{url}/score/ingest", json={
    "aa_payload": json.dumps(aa),
    "sms_dump": json.dumps(sms),
    "telecom_meta": json.dumps(tel)
})
ing = resp.json()["ingestion_id"]
print("ingestion_id:", ing)

print(requests.post(f"{url}/score/run", json={"ingestion_id": ing}).json())
```