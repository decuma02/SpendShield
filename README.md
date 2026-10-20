# SpendShield

**An Intelligent Security Firewall for AI-Powered Payments**

SpendShield is a security control layer that intercepts, evaluates, and enforces policy on purchase proposals made by AI agents before any real payment is executed. It combines a deterministic policy engine with an Isolation Forest anomaly-detection model to produce allow/block/review decisions, and integrates with the PayPal Orders API sandbox to demonstrate a complete payment-security lifecycle.

---

## Planning Documents

The following documents contain the complete architecture, security model, and implementation plan. The implementing agent should read these before writing any code.

| Document | Purpose |
|---|---|
| [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) | Product scope, MVP requirements, user journeys, success criteria, 25-day roadmap |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture, Mermaid diagrams, component responsibilities, API overview, deployment design |
| [docs/SECURITY_AND_PAYMENTS.md](docs/SECURITY_AND_PAYMENTS.md) | Threat model, policy engine rules, PayPal integration plan, idempotency, audit strategy |
| [docs/ML_PLAN.md](docs/ML_PLAN.md) | Synthetic data simulator, feature engineering, Isolation Forest training, evaluation methodology |
| [docs/IMPLEMENTATION_BACKLOG.md](docs/IMPLEMENTATION_BACKLOG.md) | Ordered implementation tasks with acceptance criteria and file locations |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Architectural decisions, rationale, open questions, and non-negotiable constraints |

---

## Project Status

> **Phase:** Planning complete. Implementation not yet started.  
> Start with [docs/IMPLEMENTATION_BACKLOG.md](docs/IMPLEMENTATION_BACKLOG.md) — TASK-001.

---

## Planned Repository Structure

```
SplendShield/
├── backend/                  # Python + FastAPI backend
│   ├── app/
│   │   ├── main.py           # FastAPI app entry point
│   │   ├── config.py         # Environment variable loading
│   │   ├── api/              # Route handlers
│   │   ├── db/               # SQLModel models and session
│   │   ├── policy/           # Deterministic policy engine
│   │   ├── ml/               # ML scorer
│   │   ├── integrations/     # PayPal client
│   │   ├── decision.py       # Decision coordinator
│   │   ├── review.py         # Human review workflow
│   │   ├── audit.py          # Audit logger
│   │   └── webhooks.py       # PayPal webhook handler
│   ├── tests/
│   └── requirements.txt
├── frontend/                 # Vite + React + TypeScript dashboard
│   ├── src/
│   │   ├── pages/            # Overview, Transactions, ReviewQueue, Policies
│   │   ├── components/
│   │   └── api/              # API client and TypeScript types
│   └── package.json
├── agent/                    # AI shopping agent (controlled Python script)
│   └── simulate.py
├── ml/
│   └── models/               # Trained model artifacts
├── scripts/                  # Offline data generation and training
│   ├── generate_synthetic_data.py
│   ├── train_model.py
│   └── evaluate_model.py
├── data/                     # Synthetic transaction data (generated)
├── docs/                     # Planning documents
├── .env.example              # Environment variable template
└── README.md
```

---

## Quick Start (local development)

### Prerequisites
- Python 3.11+
- Node.js 20+
- PayPal sandbox developer account (required for payment flow)

### 1. Clone and set up environment
```bash
git clone <repo-url>
cd SplendShield
cp .env.example .env
# Edit .env and fill in your PayPal sandbox credentials
```

### 2. Start the backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Start the frontend
```bash
cd frontend
npm install
npm run dev
# Dashboard available at http://localhost:5173
```

### 4. Train the ML model (first time only)
```bash
python scripts/generate_synthetic_data.py
python scripts/train_model.py
```

### 5. Run tests
```bash
cd backend
pytest tests/
```

---

## Running the Demo

Once the backend and frontend are running:

1. Open the dashboard at `http://localhost:5173`.
2. Navigate to the Overview page.
3. Click **Run Demo** to execute all 8 pre-scripted scenarios.
4. Watch the Transactions view update in real-time.
5. Check the Review Queue for any proposals requiring human action.

---

## Environment Variables

See [`.env.example`](.env.example) for all required variables. Key variables:

| Variable | Description |
|---|---|
| `DATABASE_URL` | SQLite path (e.g., `sqlite:///./spendshield.db`) |
| `PAYPAL_CLIENT_ID` | PayPal sandbox app Client ID |
| `PAYPAL_CLIENT_SECRET` | PayPal sandbox app Secret |
| `PAYPAL_WEBHOOK_ID` | PayPal registered webhook ID |
| `SS_API_KEY` | SpendShield API key (leave empty to disable auth in dev) |
| `ML_MODEL_PATH` | Path to trained Isolation Forest artifact |
| `REVIEW_THRESHOLD` | ML score threshold for REVIEW decision (default: 0.7) |

**Security:** Never commit real credentials. Use `.env` locally and Render/Vercel dashboard environment variables for deployment.

---

## PayPal Documentation References

The implementing agent must consult these official PayPal references:

- **Orders API v2 reference:** https://developer.paypal.com/api/orders/v2/
- **Orders API v2 schema (JSON):** https://developer.paypal.com/api/orders/v2/schema.json
- **Webhooks Management v1:** https://developer.paypal.com/api/webhooks/v1/
- **Webhook events reference:** https://developer.paypal.com/api/rest/webhooks/
- **PayPal sandbox guide:** https://developer.paypal.com/tools/sandbox/
- **Sandbox base URL:** `https://api-m.sandbox.paypal.com`

---

## Key Security Invariants

These rules must never be weakened during implementation:

1. The ML model score **cannot** override a deterministic policy BLOCK.
2. Human approval **cannot** override a deterministic policy BLOCK.
3. Payment status is **not** reported as COMPLETED without a confirmed PayPal capture response with `status=COMPLETED`.
4. The AI agent **does not** hold PayPal credentials and cannot call PayPal directly.
5. Audit events are **append-only** — no UPDATE or DELETE on `audit_events`.
6. All PayPal credentials are loaded from **environment variables only** — never committed to source code.

---

## Deployed URLs

> To be filled in after Day 23 deployment.

- **Backend:** TBD
- **Frontend:** TBD
