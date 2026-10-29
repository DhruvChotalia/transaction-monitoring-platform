"""
Train a lightweight GBT fraud classifier and save it to model/gbt_model.pkl.
Run once before starting the platform: python train.py
Uses synthetic data matching the transaction schema — no external dataset needed.
"""
import numpy as np
import joblib
import os
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import roc_auc_score

CATEGORIES = ["shopping_net", "misc_net", "grocery_pos", "gas_transport", "food_dining", "entertainment"]
CATEGORY_ENCODER = LabelEncoder().fit(CATEGORIES)

np.random.seed(42)
N = 50_000

amounts = np.random.exponential(scale=150, size=N).clip(1, 10000)
hours = np.random.randint(0, 24, size=N)
geo_dists = np.random.exponential(scale=80, size=N).clip(0, 2000)
categories = np.random.choice(CATEGORIES, size=N)
days = np.random.randint(0, 7, size=N)

cat_encoded = CATEGORY_ENCODER.transform(categories)

# Fraud probability driven by known signals
fraud_score = (
    (amounts > 1000).astype(float) * 0.4
    + ((hours >= 22) | (hours <= 4)).astype(float) * 0.3
    + (geo_dists > 500).astype(float) * 0.2
    + np.isin(categories, ["shopping_net", "misc_net"]).astype(float) * 0.1
)
fraud_prob = (fraud_score / fraud_score.max()) * 0.95
labels = (np.random.random(N) < fraud_prob).astype(int)

X = np.column_stack([amounts, hours, geo_dists, cat_encoded, days])
y = labels

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

model = GradientBoostingClassifier(n_estimators=200, max_depth=4, learning_rate=0.1, random_state=42)
model.fit(X_train, y_train)

auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
print(f"Model trained — AUC-ROC: {auc:.4f}")

os.makedirs("model", exist_ok=True)
joblib.dump({"model": model, "category_encoder": CATEGORY_ENCODER}, "model/gbt_model.pkl")
print("Saved to model/gbt_model.pkl")
