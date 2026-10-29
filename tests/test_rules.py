import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'rules-engine'))

from rules import evaluate

BASE = {
    "transaction_id": "test-001",
    "amount": 50.0,
    "merchant_category": "grocery_pos",
    "merchant_name": "Loblaws",
    "cardholder_id": "CH1234",
    "hour_of_day": 14,
    "latitude": 43.6532,
    "longitude": -79.3832,
    "home_latitude": 43.6600,
    "home_longitude": -79.3900,
}


def txn(**overrides):
    return {**BASE, **overrides}


def test_no_rules_clean_transaction():
    flags = evaluate(txn())
    assert flags == []


def test_high_amount():
    flags = evaluate(txn(amount=600))
    assert "high_amount" in flags


def test_very_high_amount():
    flags = evaluate(txn(amount=2500))
    assert "very_high_amount" in flags


def test_late_night():
    flags = evaluate(txn(hour_of_day=23))
    assert "late_night" in flags

    flags_day = evaluate(txn(hour_of_day=14))
    assert "late_night" not in flags_day


def test_high_risk_category():
    flags = evaluate(txn(merchant_category="misc_net"))
    assert "high_risk_category" in flags

    flags_safe = evaluate(txn(merchant_category="grocery_pos"))
    assert "high_risk_category" not in flags_safe


def test_geo_distance():
    flags = evaluate(txn(latitude=51.5, longitude=-0.1))
    assert "high_geo_dist" in flags


def test_combined_late_night_high_risk():
    flags = evaluate(txn(hour_of_day=2, merchant_category="misc_net"))
    assert "late_night_high_risk" in flags
    assert "late_night" in flags
    assert "high_risk_category" in flags
