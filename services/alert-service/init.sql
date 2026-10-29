CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    transaction_id TEXT UNIQUE NOT NULL,
    amount FLOAT,
    merchant_category TEXT,
    merchant_name TEXT,
    cardholder_id TEXT,
    hour_of_day INT,
    day_of_week INT,
    geo_dist FLOAT,
    fraud_probability FLOAT,
    rule_flags TEXT[],
    risk_level TEXT,
    ai_explanation TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rules (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    field TEXT,
    severity TEXT NOT NULL DEFAULT 'WARNING',
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO rules (name, description, field, severity) VALUES
    ('high_amount', 'Amount exceeds $1,000', 'amount', 'CRITICAL'),
    ('very_high_amount', 'Amount exceeds $5,000', 'amount', 'CRITICAL'),
    ('late_night', 'Transaction between 22:00–04:00', 'hour_of_day', 'WARNING'),
    ('high_risk_category', 'High-risk merchant category', 'merchant_category', 'WARNING'),
    ('high_geo_dist', 'Transaction > 500km from cardholder home', 'geo_dist', 'WARNING'),
    ('late_night_high_risk', 'Late-night + high-risk category combined', 'combined', 'CRITICAL')
ON CONFLICT (name) DO NOTHING;
