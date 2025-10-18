import os, json, joblib, numpy as np
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from app.feature_engineering import features_from_aa, features_from_sms, features_from_telco

BASE = Path(os.getenv("CREDITMIND_BASE", "/mnt/data/creditmind_backend"))
MODELS = BASE/"models"
DATA_ROOT = Path("data")
MODELS.mkdir(parents=True, exist_ok=True)

aa = json.loads((DATA_ROOT/"aa_payload.json").read_text())
sms = json.loads((DATA_ROOT/"sms_dump.json").read_text())
tel = json.loads((DATA_ROOT/"telecom_meta.json").read_text())

base_feats = {}
base_feats.update(features_from_aa(aa))
base_feats.update(features_from_sms(sms))
base_feats.update(features_from_telco(tel))

feat_names = list(base_feats.keys())

X = []
y = []
rng = np.random.default_rng(123)

for i in range(500):
    row = []
    for k in feat_names:
        val = base_feats[k]
        noise = rng.normal(0, 0.05*abs(val)+1e-3)
        row.append(float(val + noise))
    X.append(row)

    income_cv = row[feat_names.index("income_regularity_cv")]
    spend_vol = row[feat_names.index("spend_volatility")]
    buffer_days = row[feat_names.index("buffer_days")]
    emi_on = row[feat_names.index("emi_ontime_rate")]
    lowbal = row[feat_names.index("low_balance_event_rate")]
    tel_reg = row[feat_names.index("telco_regularity_index")] if "telco_regularity_index" in feat_names else 0.5

    risk = 0.4*income_cv + 0.4*spend_vol + 0.6*max(0, 2-buffer_days)/2 + 0.6*(1-emi_on) + 0.3*lowbal + 0.2*tel_reg
    p_default = 1/(1+np.exp(-(risk-1.2)))
    y.append(1 if rng.uniform()<0.6*p_default+0.2 else 0)


X = np.array(X, dtype=float)
y = np.array(y, dtype=int)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)

pipe = Pipeline([("scaler", StandardScaler()), ("model", LogisticRegression(max_iter=300))])
pipe.fit(X_train, y_train)
print("Train acc:", pipe.score(X_train, y_train))
print("Test acc:", pipe.score(X_test, y_test))

joblib.dump(pipe, MODELS/"baseline.pkl")
(Path(MODELS)/"features.json").write_text(json.dumps(feat_names, indent=2))
print("Saved:", MODELS/"baseline.pkl")