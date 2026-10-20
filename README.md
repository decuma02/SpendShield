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

## Hackathon Submission Checklist

| Requirement | Status | Details |
|---|---|---|
| **Public GitHub Repository** | Complete | [https://github.com/decuma02/SplendShield](https://github.com/decuma02/SplendShield) |
| **README Documentation** | Complete | Setup, execution, testing, architecture, and threat model included below |
| **Reproducible Dockerfile** | Complete | Single-command multi-service setup (`docker compose up --build`) |
| **Single-Command Testing** | Complete | Automated test runner (`./scripts/test.sh` or `docker compose run test`) |
| **Live Deployment** | Configured | Render (Backend) + Vercel (Frontend) deployment configs ready |
| **Demo Video** | Ready | Script & recording checklist documented in `docs/PROJECT_PLAN.md` (Video link: TBD) |

---

## OmniRush Reproducibility: Single-Command & Docker Setup

To ensure seamless evaluation for the **Best Use of OmniRush** category, SpendShield features **fully pinned dependencies**, a multi-stage **Dockerfile**, and a **single-command test runner**.

### 1. Single-Command Launch (Docker Compose)
Run the entire stack (FastAPI backend, React dashboard, SQLite in WAL mode, and ML model) with one command:
```bash
docker compose up --build
```
- Frontend Dashboard: `http://localhost:5173`
- Backend API Docs (Swagger): `http://localhost:8000/docs`

### 2. Single-Command Test Suite
Execute all unit, integration, policy engine, and ML tests with one command:
```bash
# Using Docker:
docker compose run test

# Or natively:
./scripts/test.sh     # Linux/macOS
.\scripts\test.bat    # Windows
```

---

## Quick Start (Native Local Development)

### Prerequisites
- Python 3.11+
- Node.js 20+
- PayPal sandbox developer account

### 1. Clone and set up environment
```bash
git clone https://github.com/decuma02/SplendShield.git
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

### 4. Train the ML model (offline pipeline)
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
3. Click **Run Demo** to execute all 8 pre-scripted scenarios:
   - Scenario 1: Normal grocery purchase ($30) → `ALLOW`
   - Scenario 2: Over per-transaction cap ($600) → `BLOCK`
   - Scenario 3: Blocked gambling merchant → `BLOCK`
   - Scenario 4: Duplicate proposal (replay) → `IDEMPOTENT_BLOCK`
   - Scenario 5: Structuring attempt (5x $95 rapid fire) → `BLOCK`
   - Scenario 6: Anomalous merchant category / ML anomaly → `REVIEW`
   - Scenario 7: Valid purchase approved by human supervisor → `ALLOW` (Captured)
   - Scenario 8: Prompt injection attempt in description → Sanitized & Evaluated
4. Watch the Transactions view update in real-time.
5. Check the Review Queue for proposals requiring human action.

---

## Demo Video

- **Video Walkthrough Link:** `[Link to Demo Video on YouTube/Loom/Drive - TBD]`
- **Video Covers:**
  1. Overview of autonomous agent payment risk.
  2. Architecture walkthrough: Policy Engine + Isolation Forest ML + PayPal Sandbox API.
  3. Live execution of the 8 demo scenarios in the React dashboard.
  4. Real-time human review and approval flow with strict cryptographic binding.
  5. Immutable append-only audit trail and webhook verification.

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

## Live Deployed URLs

- **Backend (Render):** `https://spendshield-backend.onrender.com` (Target)
- **Frontend Dashboard (Vercel):** `https://spendshield.vercel.app` (Target)

