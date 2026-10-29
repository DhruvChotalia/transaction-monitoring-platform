"""
Tests for the ML scorer service.
Run after `make train-model` has been executed.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'ml-scorer'))

MODEL_PATH = os.path.join(os.path.dirname(__file__), '..', 'services', 'ml-scorer', 'model', 'gbt_model.pkl')


def test_model_file_exists():
    assert os.path.exists(MODEL_PATH), "Run `make train-model` first"


def test_score_returns_probability():
    if not os.path.exists(MODEL_PATH):
        pytest.skip("Model not trained yet")
    import joblib
    import numpy as np
    model = joblib.load(MODEL_PATH)
    sample = np.array([[150.0, 14, 0.5, 2]])
    prob = model.predict_proba(sample)[0][1]
    assert 0.0 <= prob <= 1.0


def test_high_risk_transaction_scores_higher():
    if not os.path.exists(MODEL_PATH):
        pytest.skip("Model not trained yet")
    import joblib
    import numpy as np
    model = joblib.load(MODEL_PATH)
    legit = np.array([[50.0, 14, 0.1, 2]])
    suspicious = np.array([[5000.0, 2, 150.0, 11]])
    prob_legit = model.predict_proba(legit)[0][1]
    prob_sus = model.predict_proba(suspicious)[0][1]
    assert prob_sus > prob_legit


@pytest.mark.asyncio
async def test_score_endpoint():
    pytest.importorskip("httpx")
    if not os.path.exists(MODEL_PATH):
        pytest.skip("Model not trained yet")
    import httpx
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(
                "http://localhost:8003/score",
                json={"amount": 500, "hour_of_day": 2, "geo_distance": 80, "category_encoded": 11},
                timeout=3.0,
            )
            assert res.status_code == 200
            data = res.json()
            assert "fraud_probability" in data
            assert "risk_level" in data
        except httpx.ConnectError:
            pytest.skip("ML scorer service not running")
