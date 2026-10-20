# SpendShield — Project Plan

> **Hackathon deadline:** 25 days from Day 1.  
> **Document status:** Planning complete. Implementation not yet started.

---

## 1. Primary User and Problem

**Primary user:** An organisation (or individual developer) that delegates purchasing authority to an AI agent — for example a personal finance assistant, a corporate procurement bot, or an automated resupply agent — and needs a security boundary that prevents that agent from making unauthorised, fraudulent, or policy-violating payments.

**Core problem:** AI agents can make purchase proposals that exceed limits, target restricted merchants, repeat payments, split transactions to evade caps, or follow malicious instructions injected by external content. No existing open-source payment-security layer intercepts and evaluates AI-originated purchase proposals before execution.

---

## 2. MVP Scope

### What the MVP does

- Accepts structured purchase proposals from a controlled AI shopping agent via a REST API.
- Runs every proposal through a **deterministic policy engine** (hard rules, non-overridable).
- Scores every proposal through an **Isolation Forest anomaly-detection model** (soft signal only).
- Produces a decision: `ALLOW`, `BLOCK`, or `REVIEW`.
- Sends `ALLOW` decisions through the **PayPal Orders API sandbox** (create → buyer-approve → capture).
- Queues `REVIEW` decisions for human action via a dashboard review queue.
- Permanently blocks `BLOCK` decisions regardless of any other input.
- Records every proposal, evaluation, decision, approval action, and payment-lifecycle event in an append-only audit log.
- Presents real-time state through a React dashboard with four views: Overview, Transactions, Review Queue, and Policies.
- Includes a pre-scripted demo runner that fires a set of labelled scenarios covering legitimate purchases, limit violations, merchant blocks, anomaly-flagged patterns, and structuring attempts.

### What the MVP explicitly does NOT do

- It does not protect PayPal payments made outside the SpendShield API. The security boundary is the SpendShield endpoint.
- It does not support multiple tenants, multi-currency wallets, or production-money transactions.
- It does not provide a general fraud-detection service for arbitrary payment providers.
- It does not implement real-time streaming, push notifications to external systems, or mobile clients.
- It does not use the PayPal Agent Toolkit or MCP integrations as required components.
- It does not claim ML-only detection of threats already caught by deterministic rules.
- It does not guarantee real-world fraud detection beyond the synthetic evaluation scenarios.

---

## 3. Main User Journeys

### Journey 1 — Legitimate purchase
Agent proposes a $45 purchase at an approved merchant → policy engine: ALLOW → ML: low anomaly score → decision: ALLOW → PayPal order created → (demo) buyer approval simulated → PayPal capture → dashboard shows COMPLETED.

### Journey 2 — Hard block
Agent proposes a $5,000 purchase exceeding per-transaction cap → policy engine: BLOCK → decision returned immediately → no PayPal order created → audit entry recorded → dashboard shows BLOCKED with reason.

### Journey 3 — Human review
Agent proposes a purchase with a moderate anomaly score and a first-time merchant → decision: REVIEW → item appears in dashboard review queue → human clicks Approve or Reject → if approved, SpendShield proceeds to PayPal order creation → audit shows human approval chain.

### Journey 4 — Structuring detection
Agent fires 5 consecutive $95 purchases within 10 minutes to circumvent a $100 per-transaction cap → rolling-window aggregate limit exceeded → BLOCK on transaction 3 → audit log shows sequence.

### Journey 5 — Rejected review
Human rejects a queued review → no payment is created → proposal marked REJECTED → dashboard reflects outcome.

---

## 4. Demo Scenarios (pre-scripted)

| Scenario | Expected decision | Key rule triggered |
|---|---|---|
| Normal $30 grocery purchase | ALLOW | None |
| $600 single purchase (cap $500) | BLOCK | Per-transaction limit |
| Restricted merchant (blacklisted) | BLOCK | Merchant restriction |
| Repeated identical proposal within 60 s | BLOCK | Duplicate detection |
| 5x $95 in 10 min (daily cap $400) | BLOCK on 5th | Rolling-window aggregate |
| Unusual merchant category + high amount | REVIEW | ML anomaly + review threshold |
| Valid purchase after review approved | ALLOW (after approval) | Human review workflow |
| Prompt injection in description field | Sanitised, ALLOW or BLOCK per amount | Input sanitisation |

---

## 5. Success Criteria

The MVP is considered presentable when all of the following are true:

1. A legitimate proposal completes the full path: SpendShield → ALLOW → PayPal sandbox order created → (simulated) approval → captured → COMPLETED in dashboard.
2. A proposal violating a hard policy rule is BLOCKED regardless of ML score, with a human-readable reason.
3. Rolling-window aggregate limits catch a structuring sequence of individually-valid transactions.
4. An anomalous proposal reaches the review queue and appears in the dashboard within one browser refresh.
5. A human can approve or reject from the dashboard, and the decision is reflected in the audit log.
6. A material change to a proposal (amount or merchant) invalidates any existing approval.
7. Duplicate proposals (same idempotency key within the deduplication window) produce the same decision, not duplicate payment operations.
8. The dashboard Overview, Transactions, Review Queue, and Policies views are functional and show live backend data.
9. The demo runner can be triggered from the dashboard and all eight demo scenarios execute and display correctly.
10. The backend returns an appropriate error or fallback if the PayPal sandbox is unreachable, without silently claiming a payment succeeded.

---

## 6. Minimum Functionality Required Before Presentable

- FastAPI backend running with SQLite persistence.
- Policy engine enforcing at minimum: per-transaction cap, daily aggregate cap, merchant block list, duplicate detection.
- Isolation Forest model loaded and scoring proposals (even if trained on minimal synthetic data).
- Decision coordinator applying deterministic-first logic.
- PayPal sandbox: order creation and capture via REST API with real credentials.
- Human review queue: approve and reject endpoints, protected against stale approvals.
- React dashboard: all four views functional with real API data.
- Demo runner endpoint that fires the eight pre-scripted scenarios.
- Audit log recording every decision and lifecycle event.

---

## 7. Stretch Goals (must NOT delay core)

- PayPal webhook listener with HMAC signature verification.
- Hash-chaining on audit log entries.
- Policy version history and rollback UI.
- Isolation Forest retraining pipeline runnable via a script.
- Multiple policy profiles (personal vs. corporate).
- A/B comparison view: rules-only vs. rules+ML decisions on the same scenario set.
- Deployment on Render (backend) and Vercel/Netlify (frontend).

---

## 8. Assumptions

- PayPal sandbox credentials can be obtained before Day 3. Implementation must not block on this.
- The AI agent is a controlled Python script that calls the SpendShield proposal API; it is not an LLM with autonomous internet access during testing.
- A single SQLite database is acceptable for the hackathon. No migration to PostgreSQL is required.
- The buyer-approval step in PayPal sandbox can be automated using the sandbox buyer account credentials (headless) for the demo, since a real browser-based OAuth redirect is not practical in a demo runner.
- A single-user dashboard with no authentication is acceptable for the hackathon prototype. API key authentication is a recommended addition but not a hard requirement.

---

## 9. 25-Day Implementation Roadmap

### Phase 1 — Foundation (Days 1–5) · Critical path

**Day 1 — Repository and environment setup**
- Initialise `backend/` as a Python project with `pyproject.toml` or `requirements.txt`.
- Initialise `frontend/` with Vite + React + TypeScript.
- Create `.env.example` with all required variable names (no values).
- Create `README.md` linking the planning docs.
- Definition of done: `uvicorn` starts, `npm run dev` starts, both reachable locally.

**Day 2 — Database schema and core models**
- Design and implement SQLAlchemy ORM models: `Proposal`, `PolicyRule`, `Decision`, `ApprovalRecord`, `AuditEvent`, `BudgetLedger`, `PaymentRecord`.
- Implement Alembic migrations (or SQLModel equivalents).
- Seed default policy values.
- Definition of done: All tables created, seed data present, models importable.

**Day 3 — Policy engine (deterministic)**
- Implement `PolicyEngine` class with rules: per-transaction cap, daily aggregate cap, merchant block list, duplicate detection, currency validation, amount validation.
- Implement `BudgetLedger` with atomic reservation and release.
- Unit tests for every rule with `pytest`.
- Definition of done: All eight demo scenarios pass policy engine unit tests.

**Day 4 — Core FastAPI API layer**
- Implement endpoints: `POST /api/v1/proposals`, `GET /api/v1/proposals`, `GET /api/v1/proposals/{id}`, `GET /api/v1/health`.
- Implement idempotency key enforcement.
- Definition of done: Can submit proposals via curl and receive deterministic decisions.

**Day 5 — PayPal sandbox proof of concept**
- Create PayPal developer account, create sandbox app, obtain `client_id` and `client_secret`.
- Implement `PayPalClient` with OAuth2 token refresh, order creation (`POST /v2/checkout/orders`), and capture (`POST /v2/checkout/orders/{id}/capture`).
- Manually test create → capture flow using sandbox buyer credentials.
- Definition of done: A sandbox order goes from CREATED to COMPLETED. Document the exact buyer-approval simulation method used.

### Phase 2 — Core SpendShield flow (Days 6–11) · Critical path

**Day 6 — ML synthetic data and model training**
- Implement `scripts/generate_synthetic_data.py` producing ~10,000 synthetic transactions across 4 behavioural categories: normal, unusual-amount, burst, structuring.
- Train Isolation Forest, save model artifact to `ml/models/isolation_forest_v1.pkl`.
- Definition of done: Script runs cleanly; model file exists; basic evaluation prints precision and detection rate.

**Day 7 — ML inference service**
- Implement `MLScorer` class that loads the saved model and returns a normalised risk score [0.0, 1.0].
- Define feature extraction from a `Proposal` object.
- Define fallback behaviour when model is unavailable (score = 0.5, decision based on policy alone).
- Unit tests for feature extraction and score range.
- Definition of done: `MLScorer.score(proposal)` returns a float; unavailable-model path tested.

**Day 8 — Decision coordinator**
- Implement `DecisionCoordinator` that combines policy engine output with ML score:
  1. If policy says BLOCK → BLOCK (final, no override).
  2. If policy says ALLOW and ML score < review threshold → ALLOW.
  3. If policy says ALLOW and ML score >= review threshold → REVIEW.
- Integrate into proposal submission endpoint.
- Definition of done: End-to-end: submit proposal → get ALLOW/BLOCK/REVIEW with reason.

**Day 9 — PayPal integration into proposal flow**
- Connect ALLOW decisions to `PayPalClient.create_order()`.
- Implement sandbox buyer approval simulation (see DECISIONS.md).
- Implement `PayPalClient.capture_order()`.
- Record `paypal_order_id`, `paypal_capture_id`, and `payment_status` in `PaymentRecord`.
- Definition of done: An ALLOW decision produces a COMPLETED `PaymentRecord` in the database with real PayPal sandbox IDs.

**Day 10 — Human review workflow**
- Implement `POST /api/v1/proposals/{id}/approve` and `POST /api/v1/proposals/{id}/reject`.
- Implement approval binding: approval is tied to a hash of `(proposal_id, amount, currency, merchant_id)`. Any change invalidates the approval.
- Implement approval expiry (TTL configurable, default 30 minutes).
- Trigger PayPal order creation on approval confirmation.
- Definition of done: Approve flow creates a PayPal order. Stale or modified approval returns 409.

**Day 11 — Audit log and budget reconciliation**
- Implement `AuditLogger` with append-only inserts.
- Implement `GET /api/v1/audit` endpoint.
- Implement `GET /api/v1/proposals/{id}/audit` endpoint.
- Implement budget release on payment failure or rejection.
- Definition of done: Every decision and lifecycle event appears in the audit trail. Budget returns to available on failure.

### Phase 3 — Dashboard (Days 12–17)

**Day 12 — API client and shared types**
- Generate or write TypeScript API client types matching backend response shapes.
- Implement React Query (or SWR) data-fetching hooks.
- Definition of done: Frontend can fetch and display a list of proposals from the running backend.

**Day 13 — Overview and Transactions views**
- Implement Overview: counts, spending summary, recent decisions.
- Implement Transactions: AG Grid table with proposal details, decision, risk score, payment status.
- Definition of done: Both views render real backend data with loading and error states.

**Day 14 — Review Queue view**
- Display pending REVIEW proposals.
- Implement Approve and Reject buttons with confirmation dialog.
- Show clear reason for review, proposal details, and staleness warning if nearing TTL.
- Definition of done: Human can approve or reject from the browser; page updates without manual refresh.

**Day 15 — Policies view**
- Display current policy values: per-transaction cap, daily cap, block list, review threshold.
- Implement inline editing with validation.
- `PATCH /api/v1/policies` endpoint.
- Definition of done: Policy change persists and affects subsequent proposals.

**Day 16 — Demo runner**
- Implement `POST /api/v1/demo/run` endpoint that fires eight pre-scripted scenarios sequentially with artificial delays.
- Implement demo status endpoint `GET /api/v1/demo/status`.
- Add "Run Demo" button to Overview dashboard.
- Definition of done: All eight scenarios execute and their outcomes appear in the Transactions view.

**Day 17 — Dashboard polish and error states**
- Loading skeletons, empty states, error banners.
- Responsive layout for 1280px minimum width.
- Definition of done: Dashboard looks professional; no uncaught errors in the browser console.

### Phase 4 — Security, testing, and integration (Days 18–22)

**Day 18 — Security hardening**
- Input sanitisation for all string fields (description, merchant name).
- API key middleware for all non-webhook endpoints (configurable).
- Rate limiting on proposal submission.
- Ensure no secrets appear in logs or API responses.

**Day 19 — Webhook listener (stretch-priority)**
- Implement `POST /api/v1/webhooks/paypal` endpoint.
- Implement HMAC signature verification using `PAYPAL-TRANSMISSION-SIG` header.
- Update `PaymentRecord` on `PAYMENT.CAPTURE.COMPLETED` and `PAYMENT.CAPTURE.DENIED`.
- Register webhook in PayPal developer dashboard.
- Definition of done: PayPal sandbox can deliver a simulated event and the database reflects the updated status.

**Day 20 — Integration and concurrency tests**
- Test duplicate request idempotency.
- Test concurrent proposals attempting to exceed a daily cap.
- Test stale approval rejection.
- Test ML model unavailable fallback.
- Test PayPal sandbox error handling.
- Definition of done: All tests pass without race conditions on concurrent proposals.

**Day 21 — ML evaluation report**
- Run held-out scenarios through three configurations: rules-only, rules+aggregate limits, rules+ML.
- Compute precision, detection rate, false-positive rate for each configuration.
- Document results in `docs/ML_PLAN.md` under "Evaluation Results".
- Definition of done: Report includes honest caveats about synthetic data.

**Day 22 — End-to-end testing**
- Manual end-to-end walkthrough of all eight demo scenarios.
- Fix any issues found.
- Definition of done: All eight scenarios produce expected outcomes confirmed by both dashboard state and database inspection.

### Phase 5 — Deployment and demo preparation (Days 23–25)

**Day 23 — Deployment**
- Deploy backend to Render (free tier, Python web service).
- Deploy frontend to Vercel or Netlify.
- Configure environment variables in Render dashboard.
- Definition of done: Both services reachable at public URLs; end-to-end demo runs against deployed services.

**Day 24 — Demo rehearsal**
- Script and rehearse the demo narrative.
- Record a backup screen-capture video of the demo running correctly.
- Write a short demo guide.
- Definition of done: Demo can be delivered end-to-end in under 10 minutes.

**Day 25 — Buffer, bug fixes, and final documentation**
- Fix any issues from rehearsal.
- Review all planning documents for accuracy.
- Final commit and tag `v0.1.0-mvp`.
- Definition of done: Repository is clean, all planning docs accurate, demo video exists.

---

## 10. Critical-Path Dependencies

```
Day 1 (env) → Day 2 (DB) → Day 3 (policy) → Day 4 (API) → Day 9 (PayPal in flow)
                                             → Day 6 (ML data) → Day 7 (ML scorer) → Day 8 (coordinator)
Day 4 (API) → Day 10 (review workflow)
Day 4 (API) → Day 12 (frontend client) → Days 13-16 (dashboard)
Day 5 (PayPal PoC) → Day 9 (PayPal in flow) — external dependency; must succeed by end of Day 5
```

**Biggest external risk:** PayPal sandbox buyer-approval automation. If a browser redirect is required and cannot be automated headlessly, the demo must use a fallback (see `DECISIONS.md`, Decision D-05). This must be resolved by end of Day 5.

---

## 11. Parallelisable Work

- Frontend (Days 12–16) can run in parallel with security hardening and testing (Days 18–21) once API contracts are stable after Day 11.
- ML training and evaluation (Days 6–7 and Day 21) can run in parallel with API development from Day 4 onward.
- Demo runner (Day 16) can be developed in parallel with dashboard polish (Day 17).
