import os

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

app = FastAPI(title="ML Scorer Service", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
Instrumentator().instrument(app).expose(app)

MODEL_PATH = os.getenv("MODEL_PATH", "model/gbt_model.pkl")

_artifacts: dict | None = None


def load_model():
    global _artifacts
    if _artifacts is None:
        if not os.path.exists(MODEL_PATH):
            raise RuntimeError(f"Model not found at {MODEL_PATH}. Run train.py first.")
        _artifacts = joblib.load(MODEL_PATH)
    return _artifacts


class Transaction(BaseModel):
    transaction_id: str
    amount: float
    merchant_category: str
    hour_of_day: int
    day_of_week: int
    geo_dist: float
    cardholder_id: str | None = None
    merchant_name: str | None = None


@app.get("/health")
def health():
    try:
        load_model()
        return {"status": "ok", "service": "ml-scorer", "model": "loaded"}
    except RuntimeError:
        return {"status": "degraded", "service": "ml-scorer", "model": "not_found"}


@app.post("/score")
def score(txn: Transaction):
    try:
        arts = load_model()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    model = arts["model"]
    enc = arts["category_encoder"]

    try:
        cat_encoded = enc.transform([txn.merchant_category])[0]
    except ValueError:
        cat_encoded = 0

    features = np.array([[txn.amount, txn.hour_of_day, txn.geo_dist, cat_encoded, txn.day_of_week]])
    fraud_prob = float(model.predict_proba(features)[0][1])

    return {
        "transaction_id": txn.transaction_id,
        "fraud_probability": round(fraud_prob, 4),
        "risk_level": "HIGH" if fraud_prob >= 0.7 else "MEDIUM" if fraud_prob >= 0.4 else "LOW",
    }
