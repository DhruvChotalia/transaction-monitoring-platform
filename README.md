# Real-Time Transaction Monitoring Platform

A production-grade, event-driven microservices platform that ingests financial transactions, applies hybrid rule-based + ML fraud scoring, generates AI-powered plain-English explanations for every flagged alert, and streams everything live to a React dashboard — with Prometheus + Grafana observability and full Kubernetes deployment manifests.

[![CI](https://github.com/DhruvChotalia/transaction-monitoring-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/DhruvChotalia/transaction-monitoring-platform/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)
![React](https://img.shields.io/badge/React-18-61DAFB)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)

---

## Architecture

```
Simulation Script / Client
         │  POST /transactions (JWT)
         ▼
┌────────────────────────┐
│   API Gateway  :8000   │  FastAPI · JWT auth · Rate limiting · OpenAPI docs
└──────────┬─────────────┘
           │ Redis Pub/Sub → raw_transactions
           ▼
┌────────────────────────┐
│  Ingestion Svc  :8001  │  FastAPI · Redis producer · Writes raw event → MongoDB
└──────────┬─────────────┘
           │ Redis Pub/Sub → raw_transactions
           ▼
┌────────────────────────┐
│  Rules Engine   :8002  │  Redis consumer · 6 fraud rules (amount, geo-distance,
│                        │  time-of-day, category risk) · calls ML Scorer via HTTP
└──────────┬─────────────┘
           │ HTTP POST → /score
           ▼
┌────────────────────────┐
│  ML Scorer      :8003  │  FastAPI · GBT model (scikit-learn) · returns fraud_prob
└──────────┬─────────────┘
           │ Redis Pub/Sub → flagged_alerts (if prob ≥ 0.60 or CRITICAL rule)
           ▼
┌────────────────────────┐
│  Alert Service  :8004  │  Redis consumer · Writes structured alert → PostgreSQL
└──────────┬─────────────┘  · Republishes to live_alerts for WebSocket broadcast
           │ async HTTP
           ▼
┌────────────────────────┐
│  AI Explainer   :8005  │  FastAPI · LangChain + Claude API · generates plain-English
│                        │  explanation per alert · stores result in PostgreSQL
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│  Dashboard API  :8006  │  FastAPI + WebSocket · serves live alerts, stats,
│                        │  analytics, rule performance to the React frontend
└──────────┬─────────────┘
           │
           ▼
┌────────────────────────┐
│  React Frontend :3000  │  Vite + React 18 + TypeScript + Recharts
│                        │  Live alert feed · AI explanation panel ·
│                        │  Hourly heatmap · Category breakdown · Dark mode
└────────────────────────┘

Observability (optional overlay):
  Prometheus :9090 — scrapes /metrics from all 7 FastAPI services
  Grafana    :3001 — pre-built dashboard: request rate, p99 latency, error rate
```

---

## Tech Stack

| Layer | Technologies |
|---|---|
| **API Services** | Python 3.11, FastAPI, asyncio, Pydantic v2 |
| **ML / AI** | scikit-learn (GBT), joblib, LangChain, Claude API (Haiku) |
| **Message Bus** | Redis 7 Pub/Sub (3 channels) |
| **Databases** | PostgreSQL 15 (alerts), MongoDB 7 (raw events), Redis (ephemeral) |
| **Frontend** | React 18, TypeScript, Vite, Recharts, Axios, WebSocket |
| **DevOps** | Docker, Docker Compose, Kubernetes, GitHub Actions CI |
| **Observability** | Prometheus, Grafana, structured logging |
| **Auth** | JWT (HS256), python-jose, FastAPI Security |

---

## Quickstart

### Prerequisites
- Docker Desktop + Docker Compose
- Python 3.11 (for model training)

```bash
# 1. Clone and configure
git clone https://github.com/DhruvChotalia/transaction-monitoring-platform.git
cd transaction-monitoring-platform
cp .env.example .env
# (optional) add your ANTHROPIC_API_KEY to .env for AI explanations

# 2. Train the fraud detection model
make train-model

# 3. Start all 8 services
make up

# 4. Open the dashboard
open http://localhost:3000

# 5. Send 10,000 simulated transactions and watch the dashboard light up
make simulate
```

The dashboard will show alerts populating in real time via WebSocket. Click any alert to see the AI-generated explanation.

---

## Make Targets

| Command | Description |
|---|---|
| `make up` | Build and start all containers |
| `make down` | Stop and remove containers + volumes |
| `make train-model` | Train GBT fraud model (run once before `make up`) |
| `make simulate` | Send 10,000 synthetic transactions for live demo |
| `make test` | Run full pytest suite (unit + integration) |
| `make logs` | Tail logs from all services |
| `make monitoring` | Start Prometheus + Grafana overlay |
| `make k8s` | Deploy to local Kubernetes (minikube) |
| `make k8s-down` | Remove Kubernetes deployments |

---

## Services

### API Gateway (`:8000`)
- JWT authentication on all routes except `/health` and `/auth/login`
- Rate limiting: 100 requests/minute per IP (slowapi)
- Reverse-proxies to ingestion, dashboard-api, and ai-explainer
- Auto-generated OpenAPI docs at `/docs`

### Rules Engine (`:8002`)
Six configurable fraud rules evaluated per transaction:

| Rule | Trigger | Severity |
|---|---|---|
| `high_amount` | amount > $500 | WARNING |
| `very_high_amount` | amount > $2,000 | CRITICAL |
| `late_night` | hour in 22–3 | WARNING |
| `high_risk_category` | misc_net, misc_pos, crypto | WARNING |
| `high_geo_dist` | > 500 km from home | CRITICAL |
| `late_night_high_risk` | late_night + high_risk_category | CRITICAL |

### ML Scorer (`:8003`)
- Gradient Boosted Tree classifier (scikit-learn)
- Features: transaction amount, hour of day, geo-distance, merchant category
- Returns `fraud_probability` (0–1) and `risk_level` (LOW / MEDIUM / HIGH)
- Model trained on 50,000 synthetic transactions; retrain with `make train-model`

### AI Explainer (`:8005`)
- LangChain + Claude Haiku (cost-efficient) generates a plain-English explanation per alert
- Example output: *"This $4,200 transaction at an online misc merchant at 2:14 AM was flagged with 0.91 fraud probability. Contributing factors: amount is 18× this cardholder's average, late-night timing, and merchant category associated with elevated fraud rates. The geographic distance of 520 km from the cardholder's home address further increases suspicion."*
- Falls back to rule-based explanation if no API key configured

---

## Project Structure

```
transaction-monitoring-platform/
├── services/
│   ├── api-gateway/         # JWT auth, rate limiting, proxy routes
│   ├── ingestion/           # Transaction intake, Redis pub, MongoDB write
│   ├── rules-engine/        # Redis consumer, 6 fraud rules, ML scorer call
│   ├── ml-scorer/           # GBT model endpoint + train script
│   ├── alert-service/       # PostgreSQL writes, live_alerts broadcast
│   ├── ai-explainer/        # LangChain + Claude API explanations
│   └── dashboard-api/       # WebSocket, REST analytics, rule management
├── frontend/                # React 18 + TypeScript + Recharts dashboard
├── simulation/              # 10,000-transaction demo script
├── tests/                   # pytest unit + integration tests
├── k8s/                     # Kubernetes manifests (11 files)
├── monitoring/              # Prometheus scrape config + Grafana dashboard JSON
├── .github/workflows/       # GitHub Actions CI (lint → test → docker build)
├── docker-compose.yml       # Full local stack
├── docker-compose.monitoring.yml  # Prometheus + Grafana overlay
└── Makefile
```

---

## Fraud Detection Model

The GBT classifier is adapted from a companion fraud analytics project ([Fraud Loss Analytics](https://github.com/DhruvChotalia/fraud-loss-analytics)) that analyzed 1.85M real transactions. The model here is trained on synthetic data with similar statistical properties — it deliberately links the two portfolio projects to demonstrate domain continuity.

**Model performance** (synthetic test set, 50k transactions, 15% fraud rate):
- AUC-ROC: ~0.93
- Precision at 0.6 threshold: ~0.81
- Recall at 0.6 threshold: ~0.76

---

## Kubernetes Deployment

```bash
# Start minikube
minikube start --memory=4096

# Deploy infra + all services
make k8s

# Watch pods come up
kubectl get pods -w

# Access the frontend
minikube service frontend
```

All 11 manifests are in `k8s/`. Each service has readiness and liveness probes. The API Gateway and ML Scorer are configured with 2 replicas for horizontal scaling.

---

## CI/CD

GitHub Actions runs on every push to `main`:
1. **Lint** — ruff checks all Python services, tests, and simulation scripts
2. **Unit tests** — `test_rules.py` and `test_ml_scorer.py` (no Docker required)
3. **Docker build** — parallel build of all 8 service images
4. **Integration tests** — full stack `docker compose up`, then `test_pipeline.py`

---

## Observability

```bash
# Start Prometheus + Grafana alongside the main stack
make monitoring

# Grafana dashboard
open http://localhost:3001  # admin / admin
```

The pre-built Grafana dashboard shows:
- HTTP request rate per service
- P99 request latency
- ML Scorer inference latency (p95)
- AI Explainer latency (p95)
- Alert ingestion rate
- Error rate %

---

## Key Design Decisions

**Why Redis Pub/Sub over Kafka?** For a portfolio project, Redis keeps the dependency footprint minimal while still demonstrating event-driven architecture. The channels are intentionally named to map directly to Kafka topics if scaling requires it.

**Why three separate databases?** Each data store is used for what it's best at: Redis for ephemeral, low-latency event routing; MongoDB for schemaless raw event archival (transactions can have variable fields); PostgreSQL for structured, queryable alerts with ACID guarantees.

**Why LangChain over a raw API call?** Demonstrates awareness of the agentic AI tooling ecosystem — relevant to most 2026 SWE roles. The chain is also easily extended to RAG (retrieving cardholder history) or multi-step reasoning.
