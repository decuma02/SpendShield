# SpendShield — Architectural Decisions

> **Format:** Each decision records the question, the chosen answer, the rationale, alternatives considered, and open questions or verification steps required.  
> Items marked **[OPEN]** are unresolved and must be investigated before implementation proceeds past the indicated task.

---

## D-01: Database — SQLite for MVP

**Status:** DECIDED  
**Relevant task:** TASK-004  

**Decision:** Use SQLite (via SQLModel/SQLAlchemy) as the persistence layer for the hackathon MVP.

**Rationale:**
- No external database server to provision, configure, or pay for.
- SQLite + WAL mode handles the low-to-moderate concurrency of a hackathon demo.
- SQLModel (Pydantic + SQLAlchemy) provides type-safe models and straightforward migration path to PostgreSQL.
- Render free tier does not provide a managed database; SQLite on ephemeral disk is acceptable for demo purposes.

**Alternatives considered:**
- PostgreSQL on Render: requires paid tier or external provider; adds setup complexity for no hackathon benefit.
- TinyDB / JSON file: no transaction support; not suitable for atomic budget reservations.

**Consequences:**
- Database resets on Render redeploy (ephemeral disk). Acceptable for demo; warn in deployment docs.
- Concurrency is limited to a single writer at a time. Use `BEGIN IMMEDIATE` transactions for budget reservations.
- If the project progresses beyond the hackathon, replace SQLite with PostgreSQL and run Alembic migrations.

---

## D-02: ORM — SQLModel over raw SQLAlchemy

**Status:** DECIDED  
**Relevant task:** TASK-004  

**Decision:** Use SQLModel (Pydantic v2-compatible) for database models and API schemas.

**Rationale:**
- SQLModel unifies the SQLAlchemy ORM model and Pydantic validation schema into a single class, reducing duplication.
- FastAPI uses Pydantic natively; SQLModel integrates without extra glue code.
- Actively maintained by the FastAPI author; well-documented.

**Alternatives considered:**
- SQLAlchemy + separate Pydantic schemas: more flexible but more boilerplate for a hackathon.
- Tortoise-ORM: async-native but less familiar and smaller ecosystem.

**Verification needed:** Confirm SQLModel's compatibility with `Decimal` fields and UUID primary keys on the target Python version (3.11+) before TASK-004 begins.

---

## D-03: ML model artifact — committed to repository

**Status:** DECIDED (with caveat)  
**Relevant task:** TASK-008  

**Decision:** Commit the trained Isolation Forest model artifact (`ml/models/isolation_forest_v1.pkl`) to the repository if its file size is under 20 MB. If larger, store a URL and download on first startup.

**Rationale:**
- Simplifies deployment: no external model registry, no S3 bucket, no additional credentials.
- Isolation Forest with 200 estimators on ~10,000 synthetic rows is typically 1–5 MB (well under the limit).
- The model contains no personally identifiable information (trained on synthetic data).

**Alternatives considered:**
- MLflow model registry: significant infrastructure overhead for a hackathon.
- Download from GitHub Releases: adds startup complexity and network dependency.

**Verification needed:** Run TASK-008 and check the file size before deciding. If > 20 MB, implement a startup download from a public URL (e.g., GitHub Releases asset).

---

## D-04: API authentication — optional API key for MVP

**Status:** DECIDED  
**Relevant task:** TASK-019  

**Decision:** Implement `X-API-Key` header authentication for all API endpoints except `/health` and `/webhooks/paypal`. When `SS_API_KEY` is empty, skip authentication (development mode).

**Rationale:**
- The demo requires calling the API from the frontend and the agent script without browser-based login.
- A single shared API key is sufficient security for a sandbox hackathon project.
- Production-grade auth (OAuth2, JWT, user accounts) is out of scope.

**Alternatives considered:**
- No authentication: acceptable for a pure demo but makes the API completely open if deployed.
- JWT with user accounts: significant implementation overhead for no hackathon benefit.

**Consequences:**
- Dashboard must include the API key in every request header (`X-API-Key: <value>`).
- The key value must be stored in `VITE_API_KEY` frontend environment variable and in `SS_API_KEY` backend environment variable.
- Security note: the API key will be visible in browser network requests. This is acceptable for a sandbox demo with no real data.

---

## D-05: PayPal sandbox buyer approval simulation [OPEN]

**Status:** OPEN — must be resolved on Day 5 (TASK-007)  
**Relevant tasks:** TASK-007, TASK-011, TASK-012  

**Question:** How does the demo runner automate buyer approval in the PayPal sandbox without a real browser redirect?

**Background:**  
PayPal's standard Orders API v2 flow requires the buyer to visit a PayPal-hosted URL (`https://www.sandbox.paypal.com/checkoutnow?token={order_id}`) to approve the order before capture is permitted. In the sandbox, this requires a real browser interaction or a simulation workaround.

**Options being investigated:**

**Option A — Sandbox buyer REST API (preferred if available)**
Some PayPal sandbox environments allow directly approving an order via a POST to a sandbox-specific endpoint using the buyer account credentials. Reference: community reports of `POST /v1/payment/payment/{id}/execute` (legacy v1) or similar sandbox-only APIs. **Must be verified experimentally.**

**Option B — Playwright headless automation**
Use Playwright to navigate to the PayPal sandbox approval URL, log in with the sandbox buyer account credentials, and click "Approve". This adds a dependency (`playwright`) and requires the browser to be installed in the deployment environment.  
- For Render free tier: the Playwright browser dependency may be too large. **Must be verified.**
- For local demo: likely feasible.

**Option C — PayPal JavaScript SDK with sandbox nonce (demo only)**  
Some PayPal sandbox flows with the JS SDK allow simulating approval programmatically. **Not yet verified for server-side use.**

**Option D — Fallback: skip approval step for demo (documented workaround)**
For the demo runner only: after creating a sandbox order, attempt capture directly. In some sandbox configurations, capture on a CREATED (not yet APPROVED) order may return an error, but in others (e.g., with specific sandbox settings), it may be permitted. **Must be tested experimentally.**  
If Option D is used: document clearly in the demo narrative that buyer approval would be required in a real production flow, and that the demo simulates the approval step. Do not falsely claim the approval step is unnecessary in production.

**Decision to be made:** Whichever option succeeds on Day 5 is the chosen approach. Update this decision record with the result before proceeding to TASK-011.

**Reference documentation:**
- PayPal Orders v2 schema: `https://developer.paypal.com/api/orders/v2/schema.json`
- PayPal developer sandbox guide: `https://developer.paypal.com/tools/sandbox/`
- PayPal webhook simulation: `https://developer.paypal.com/api/webhooks/v1.md` (simulate-event endpoint)

---

## D-06: Budget reservation concurrency model

**Status:** DECIDED  
**Relevant task:** TASK-005  

**Decision:** Use SQLite `BEGIN IMMEDIATE` transactions for budget reservation. Compute the current window total and insert the reservation in a single transaction.

**Rationale:**
- SQLite `BEGIN IMMEDIATE` acquires a write lock at the start of the transaction, preventing other writers from reading a stale total concurrently.
- For a single-process FastAPI + Uvicorn deployment (the hackathon setup), this is sufficient.
- No external locking mechanism (Redis, Postgres advisory lock) required.

**Limitation:** In a multi-process or multi-worker deployment, SQLite's file locking is the concurrency mechanism. This limits throughput but is acceptable for the hackathon. If multiple Uvicorn workers are needed, switch to PostgreSQL with `SELECT ... FOR UPDATE` on the budget ledger row.

---

## D-07: Agent implementation — controlled script, not autonomous LLM

**Status:** DECIDED  

**Decision:** The AI shopping agent for the hackathon is a controlled Python script (`agent/simulate.py`) that submits pre-defined proposals to the SpendShield API. It is not an autonomous LLM with real-time internet access.

**Rationale:**
- An autonomous LLM agent introduces unpredictable behaviour that makes demo reliability poor.
- The demo must be reliable and repeatable within 10 minutes.
- The security claims of SpendShield are better demonstrated by showing that specific attack patterns (structuring, duplicates, over-limit) are blocked, which requires deterministic scenario inputs.
- A deterministic agent controlled by the demo runner endpoint (TASK-018) demonstrates the security boundary clearly without depending on LLM output quality.

**Note for presentation:** The product concept covers AI agents generally (including autonomous LLMs). The demo uses a scripted agent for reliability. Acknowledge this distinction in the demo narrative — the SpendShield API is designed to work with any agent that calls it, including autonomous ones.

---

## D-08: Decimal handling for amounts

**Status:** DECIDED  
**Relevant task:** TASK-004  

**Decision:** Store amounts as `NUMERIC` in SQLite (via SQLAlchemy `Numeric(precision=12, scale=2)`) and use Python `Decimal` throughout. Never use `float` for monetary amounts.

**Rationale:** Floating-point arithmetic is not suitable for monetary calculations. `Decimal` with scale=2 provides exact representation of amounts to the cent.

**Implementation note:** Pydantic v2 with SQLModel supports `Decimal` fields. Ensure the Pydantic validator enforces `max_digits=12` and `decimal_places=2`.

---

## D-09: Frontend framework — Vite + React + TypeScript

**Status:** DECIDED  
**Relevant task:** TASK-003  

**Decision:** Use Vite + React + TypeScript for the frontend. No Next.js (server-side rendering not needed for this dashboard).

**Rationale:**
- Vite provides fast local development and simple static asset builds for Vercel/Netlify deployment.
- React + TypeScript is the most widely known frontend stack and fits the hackathon timeline.
- No SEO requirements; the dashboard is a protected tool, not a public marketing page.
- AG Grid's React wrapper (`ag-grid-react`) is well-supported.

---

## D-10: Webhook verification — use PayPal verify-webhook-signature API

**Status:** DECIDED  
**Relevant task:** TASK-020  

**Decision:** Verify incoming PayPal webhooks by calling `POST https://api-m.sandbox.paypal.com/v1/notifications/verify-webhook-signature` with the raw request body and all PayPal-provided headers.

**Rationale:**
- This is PayPal's recommended verification method as documented in the webhooks API.
- Local HMAC verification requires downloading and caching the PayPal certificate, which adds complexity.
- The verify-webhook-signature API handles certificate rotation automatically.

**Limitation:** The verification call is a network round-trip to PayPal, adding ~100–500ms to webhook handling. Acceptable for low-volume demo webhooks.

**Alternative considered:** Local certificate-based HMAC verification using `PAYPAL-CERT-URL`. This is more robust for production (no additional API call) but adds certificate lifecycle management complexity.

---

## D-11: Deployment — Render (backend) + Vercel (frontend)

**Status:** DECIDED (contingent on free-tier availability)  
**Relevant task:** TASK-024, TASK-025  

**Decision:** Deploy backend to Render free tier (Python web service) and frontend to Vercel free tier (static deployment).

**Rationale:**
- Both services offer free tiers suitable for hackathon demos.
- Render supports Python natively; no Docker required for basic deployment.
- Vercel has zero-configuration deployment for Vite projects.

**Risk:** Render free-tier services spin down after 15 minutes of inactivity. The first request after spin-down takes ~30 seconds. For the demo, trigger a warm-up request before presenting.

**Mitigation:** Keep a browser tab open on the health check endpoint during the demo. Add a note in the demo guide to warm up the backend 2 minutes before presenting.

---

## Open Questions Summary

| ID | Question | Must be resolved by | Risk if unresolved |
|---|---|---|---|
| D-05 | PayPal sandbox buyer approval automation method | Day 5 | Demo cannot show ALLOW → COMPLETED flow |
| D-03 | Model file size > 20 MB | Day 8 | Need to add startup download logic |
| D-02 | SQLModel Decimal/UUID compatibility | Day 2 | May need raw SQLAlchemy for affected fields |

---

## Decisions That Are Final and Must Not Be Weakened

1. **ML model cannot override a policy BLOCK.** Decision coordinator checks policy first; BLOCK is terminal.
2. **Human approval cannot override a policy BLOCK.** Approve endpoint checks proposal status; BLOCKED proposals are not approvable.
3. **PayPal credentials are never stored in source code, committed files, or API responses.**
4. **Audit events are append-only.** No UPDATE or DELETE on `audit_events` in any code path.
5. **Payment status is not reported as COMPLETED without a confirmed PayPal capture response with `status=COMPLETED`.**
6. **The agent does not hold PayPal credentials.** It can only call the SpendShield API.
