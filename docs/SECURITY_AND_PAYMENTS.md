# SpendShield — Security and Payments

> **Document status:** Planning phase. No implementation exists yet.

---

## 1. Threat Model

### Actors and trust levels

| Actor | Trust level | Notes |
|---|---|---|
| AI Shopping Agent | Untrusted | Identified by API key; all proposal fields treated as unverified |
| Human Reviewer | Trusted for approval actions | Actions are bound to a specific proposal hash |
| PayPal Sandbox | Conditionally trusted | HTTPS + signature verification required for webhooks |
| Dashboard (React) | Trusted read; bounded write | Can approve/reject only; cannot modify proposal fields |
| Backend itself | Trusted | The sole authority for policy enforcement and payment execution |

### Threats and mitigations

#### T-01: Exceeding per-transaction cap
**Attack:** Agent proposes an amount above the configured cap.  
**Mitigation:** Policy engine rule P-01 checks `amount > MAX_PER_TRANSACTION_USD` and returns BLOCK before any PayPal call.

#### T-02: Exceeding aggregate/rolling-window spending limit
**Attack:** Agent fires multiple individually-valid proposals to exhaust a budget.  
**Mitigation:** Policy engine rule P-02 uses an atomic budget reservation in `budget_ledger`. Each reservation is committed before the response is returned. Concurrent proposals that together would exceed the cap are blocked at the reservation step.

#### T-03: Purchase structuring (splitting to evade per-transaction cap)
**Attack:** Agent splits a $600 purchase into six $100 proposals.  
**Mitigation:** Rules P-02 (rolling-window aggregate) and P-03 (velocity: maximum N proposals per hour per agent) catch this pattern deterministically. ML also flags burst behaviour.

#### T-04: Restricted or untrusted merchant
**Attack:** Agent proposes a purchase from a blacklisted or unknown merchant.  
**Mitigation:** Policy engine rule P-04 checks against the block list. Rule P-05 may send unknown merchants to REVIEW.

#### T-05: Duplicate or replayed proposals
**Attack:** Agent submits the same proposal twice (or a network retry), causing double payment.  
**Mitigation:** Each proposal includes an `idempotency_key`. The backend checks this key against a deduplication window (e.g., 5 minutes or until the proposal reaches a terminal state). A duplicate returns the same cached decision without creating a new payment.

#### T-06: Tampering with approved proposal details
**Attack:** After a proposal is approved for $50, the agent or an intermediary changes the amount to $500.  
**Mitigation:** Approval records store a `binding_hash = sha256(proposal_id + amount + currency + merchant_id)`. Before proceeding to PayPal, the backend recomputes the hash and rejects with 409 if it does not match the stored hash.

#### T-07: Prompt injection via purchase description
**Attack:** Malicious content in the `description` or `merchant_name` field attempts to manipulate backend logic or logging.  
**Mitigation:** All string fields are sanitised on ingestion (strip HTML, control characters, excessively long strings). Descriptions are stored as opaque strings and never executed or parsed as code. Log output is escaped.

#### T-08: Forged or replayed PayPal webhooks
**Attack:** An attacker sends a fake webhook claiming a capture is complete.  
**Mitigation:** Every incoming webhook is verified using the PayPal signature verification API (`POST /v1/notifications/verify-webhook-signature`) before acting on its content. Events already processed (by `paypal_event_id`) are idempotently skipped.

#### T-09: Race condition on budget reservation
**Attack:** Two simultaneous proposals that together exceed the daily cap are both approved because each check sees the pre-reservation balance.  
**Mitigation:** Budget reservation uses a database-level serializable transaction or a row-level lock on the `budget_ledger` row for the relevant window key. SQLite's WAL mode with correct transaction isolation provides this for single-process deployments.

#### T-10: ML score overriding hard policy
**Attack:** A proposal that violates a hard rule has a low anomaly score, tricking the coordinator into allowing it.  
**Mitigation:** Decision coordinator always evaluates policy first. If `PolicyResult.decision == BLOCK`, the coordinator returns BLOCK regardless of ML score. ML score is consulted only when policy returns ALLOW.

#### T-11: Human approval overriding hard prohibition
**Attack:** A human reviewer tries to approve a BLOCKED proposal.  
**Mitigation:** The approve endpoint checks the proposal's current status. A BLOCKED proposal's approve endpoint returns 409. Human approval is only available for REVIEW-status proposals.

#### T-12: Secrets leakage
**Attack:** PayPal credentials or API keys appear in logs, error messages, or API responses.  
**Mitigation:** Credentials are loaded from environment variables only. Log statements use structured logging with explicit field exclusion for sensitive keys. Error responses return generic messages without internal state. Pydantic response models exclude credential fields.

#### T-13: Invalid currency or malformed amounts
**Attack:** Agent submits `amount = -100` or `currency = "FAKE"`.  
**Mitigation:** Validation layer enforces: amount > 0, amount has at most 2 decimal places, currency is in the ISO 4217 allow-list (e.g., USD, EUR, GBP).

#### T-14: Abandoned checkout or expired PayPal order
**Attack:** A PayPal order is created but buyer approval never happens, leaving a budget reservation in place.  
**Mitigation:** Orders in `PAYMENT_PENDING` state for longer than a configurable TTL (default: 15 minutes) are expired by a background reconciliation task. The task releases the budget reservation and records `PAYMENT_ABANDONED` in the audit log.

---

## 2. Policy Engine Rules

Rules are evaluated in the following precedence order. The first BLOCK terminates evaluation.

| ID | Rule | Configurable | Default | Notes |
|---|---|---|---|---|
| P-01 | Per-transaction cap | Yes | $500 USD | Checked against `amount` |
| P-02 | Daily aggregate cap | Yes | $2,000 USD | Rolling 24h window per agent_id |
| P-03 | Velocity limit | Yes | 10 proposals / 60 min | Per agent_id |
| P-04 | Merchant block list | Yes (list) | Empty | Exact match on merchant_id |
| P-05 | Unknown merchant flag | Yes (bool) | REVIEW | New merchant_id not in trust list |
| P-06 | Duplicate detection | Config (window) | 5 min | Same idempotency_key within window |
| P-07 | Currency allow-list | Yes (list) | [USD, EUR, GBP] | Blocks proposals with other currencies |
| P-08 | Amount format | No | amount > 0, <= 2 dp | Hard validation |

**Rule precedence:** P-06 (duplicate) → P-08 (format) → P-01 (per-tx cap) → P-02 (aggregate) → P-03 (velocity) → P-04 (block list) → P-05 (unknown merchant).

**Policy conflict resolution:** A single proposal may trigger multiple rules. All triggered rule reasons are collected and returned. The decision is BLOCK if any rule triggers BLOCK; otherwise ALLOW (before ML scoring).

**Policy update safety:** Policy values are updated via `PATCH /api/v1/policies`. The endpoint validates input types and ranges. Policy changes take effect immediately on the next proposal. A policy version number is incremented on each change and recorded in every decision.

---

## 3. Approval Model

### Binding
Approval is tied to an immutable binding hash:
```
binding_hash = sha256(str(proposal_id) + str(amount) + currency + merchant_id)
```

Before acting on an approval, the backend recomputes this hash from the database record and compares it to the stored hash. Mismatch → 409.

### Expiry
- Approval TTL: 30 minutes (configurable via `REVIEW_APPROVAL_TTL_MINUTES`).
- After expiry: approval endpoint returns 410 Gone. Budget reservation is released.
- Expiry is enforced at the time the approve endpoint is called. No background expiry is required for MVP (background task is a stretch goal).

### Rejection finality
- A rejected proposal cannot be re-submitted under the same `idempotency_key`.
- The agent must generate a new `idempotency_key` for a re-submission after rejection.

### What approval does NOT mean
Human approval means a human has authorised the transaction to proceed to payment. It does not mean:
- The PayPal order has been created.
- The payment has been captured.
- The transaction has been completed.

The payment lifecycle steps are executed by the backend after approval, and each step's outcome is tracked independently.

---

## 4. PayPal Integration Plan

### Verified sandbox endpoints (as of 2026-10-19)
Source: `https://developer.paypal.com/api/orders/v2.md`

- **Base URL (sandbox):** `https://api-m.sandbox.paypal.com`
- **Authentication:** OAuth 2.0 client credentials (`POST /v1/oauth2/token`)
- **Create order:** `POST /v2/checkout/orders`
- **Get order:** `GET /v2/checkout/orders/{id}`
- **Capture order:** `POST /v2/checkout/orders/{id}/capture`
- **Verify webhook signature:** `POST /v1/notifications/verify-webhook-signature`

### Order creation request (minimum viable)
```json
{
  "intent": "CAPTURE",
  "purchase_units": [{
    "amount": {
      "currency_code": "USD",
      "value": "45.00"
    },
    "description": "<sanitised proposal description>"
  }]
}
```

Response contains `id` (order ID) and `status` (initially `CREATED`).

### Buyer approval (CRITICAL open question — see DECISIONS.md D-05)
The standard flow requires the buyer to visit a PayPal-hosted approval URL. For sandbox testing and demo automation, PayPal provides:
1. **Sandbox buyer REST API:** `POST https://api-m.sandbox.paypal.com/v1/payments/payment/{id}/execute` (legacy v1 — not preferred).
2. **Headless sandbox approval:** Simulate buyer approval using sandbox buyer credentials via the PayPal JS SDK or a Playwright-based automation. **Verification required on Day 5.**
3. **Fallback (if automation blocked):** Skip actual buyer approval in the demo runner; create and capture in sequence using a sandbox Personal account directly. Document clearly that this is a sandbox-only simulation and that real buyer approval would be required in production.

### Payment capture
`POST /v2/checkout/orders/{id}/capture`  
Capture response includes `purchase_units[0].payments.captures[0].status`. A value of `COMPLETED` confirms payment. Any other value (e.g., `DECLINED`, `PENDING`) must be handled — do not treat capture response receipt as success confirmation.

### Idempotency on PayPal API calls
- PayPal supports idempotency via the `PayPal-Request-Id` header on order creation.
- Use the SpendShield `proposal_id` as the `PayPal-Request-Id` to prevent duplicate orders on network retry.

### Error handling
| Scenario | Handling |
|---|---|
| 401 Unauthorized | Refresh OAuth token, retry once |
| 422 Unprocessable | Log response, return PAYMENT_FAILED; release budget |
| 429 Rate limited | Retry with exponential backoff (max 3 attempts) |
| Timeout / connection error | Return PAYMENT_FAILED; release budget; audit log entry |
| Capture status != COMPLETED | Persist actual status; do not report as completed |

### Webhook events (relevant for MVP)
Source: `https://developer.paypal.com/api/webhooks/v1.md`

- `PAYMENT.CAPTURE.COMPLETED` — update PaymentRecord to CAPTURED.
- `PAYMENT.CAPTURE.DENIED` — update PaymentRecord to FAILED; release budget.
- `CHECKOUT.ORDER.APPROVED` — informational; order has buyer approval (useful for async flows).

### Webhook signature verification
Required headers: `PAYPAL-AUTH-ALGO`, `PAYPAL-CERT-URL`, `PAYPAL-TRANSMISSION-ID`, `PAYPAL-TRANSMISSION-SIG`, `PAYPAL-TRANSMISSION-TIME`.

The backend calls `POST /v1/notifications/verify-webhook-signature` with the raw request body and these headers. PayPal returns `{"verification_status": "SUCCESS"}` or `"FAILURE"`. Only `SUCCESS` allows the event to be processed.

`PAYPAL_WEBHOOK_ID` must be stored in environment variables and must match the registered webhook in the PayPal developer dashboard.

### Account setup requirements
1. Create a PayPal developer account at `https://developer.paypal.com`.
2. Create a sandbox application in the developer dashboard.
3. Note the `Client ID` and `Secret` for the sandbox app.
4. Create a sandbox buyer account (Personal) and a sandbox seller account (Business).
5. Register the webhook URL (deployed backend URL + `/api/v1/webhooks/paypal`).
6. Subscribe to: `PAYMENT.CAPTURE.COMPLETED`, `PAYMENT.CAPTURE.DENIED`, `CHECKOUT.ORDER.APPROVED`.

### Limitations and risks
- Sandbox buyer approval via direct REST automation is not officially documented as a simple REST call. Headless browser automation (Playwright) may be required. **Must be verified experimentally on Day 5.**
- PayPal sandbox can be slow or intermittently unreliable. The backend must handle timeouts gracefully.
- The sandbox `paypal_capture_id` and `paypal_order_id` returned are real sandbox identifiers but do not represent real money.
- Live (production) PayPal credentials must NEVER be used in this project.

### Fallback if PayPal sandbox is unavailable during demo
If the PayPal sandbox is unreliable during the live demo:
1. The backend detects the failure and returns `payment_status: PAYMENT_FAILED` with a `paypal_unavailable` reason.
2. The dashboard shows PAYMENT_FAILED with a clear explanation.
3. The demo narrative explains that the security evaluation (the core product) worked correctly, and the payment step failed due to an external service issue.
4. Do NOT claim a payment succeeded when it did not.

---

## 5. Idempotency and Concurrency

### Proposal idempotency
- Each proposal carries a client-generated `idempotency_key` (UUID recommended).
- On receipt, the backend checks `SELECT * FROM proposals WHERE idempotency_key = ?`.
- If found and in a non-terminal state: return the existing decision.
- If found and in a terminal state: return the cached decision with `X-Idempotent-Replay: true`.
- If not found: proceed with evaluation.

### PayPal idempotency
- Use `proposal_id` as the `PayPal-Request-Id` on order creation.
- If a create-order call is retried (same Request-Id), PayPal returns the existing order rather than creating a duplicate.

### Budget reservation atomicity
- `budget_ledger` rows are written within a database transaction.
- For SQLite (single process): use `BEGIN IMMEDIATE` to prevent concurrent writers from seeing stale sums.
- For each proposal: check current window total + proposed amount against cap; if within cap, insert reservation row within the same transaction.

### Reconciliation
- A background task (or on-demand endpoint) checks `payment_records` for rows in `PAYMENT_PENDING` older than the checkout TTL.
- For each expired row: set `payment_status = PAYMENT_ABANDONED`, release the `budget_ledger` reservation, append audit event.

---

## 6. Audit Strategy

### What is logged

| Event | Trigger |
|---|---|
| `PROPOSAL_RECEIVED` | Proposal submitted to API |
| `POLICY_EVALUATED` | Policy engine returns result |
| `ML_SCORED` | ML scorer returns score |
| `DECISION_MADE` | Coordinator produces final decision |
| `REVIEW_QUEUED` | Proposal enters review queue |
| `HUMAN_APPROVED` | Human clicks Approve |
| `HUMAN_REJECTED` | Human clicks Reject |
| `APPROVAL_EXPIRED` | TTL elapsed without action |
| `PAYPAL_ORDER_CREATED` | PayPal API returns order_id |
| `PAYPAL_CAPTURE_ATTEMPTED` | Capture call initiated |
| `PAYPAL_CAPTURE_COMPLETED` | Capture status = COMPLETED |
| `PAYPAL_CAPTURE_FAILED` | Capture failed or non-COMPLETED status |
| `WEBHOOK_RECEIVED` | Webhook arrives at backend |
| `WEBHOOK_VERIFIED` | Signature verified successfully |
| `WEBHOOK_REJECTED` | Signature verification failed |
| `BUDGET_RESERVED` | Budget reservation written |
| `BUDGET_RELEASED` | Budget reservation released |

### Append-only enforcement
- Application code uses INSERT-only operations on `audit_events`.
- No UPDATE or DELETE is issued by any backend code path.
- For the hackathon, this is an application-level guarantee. The SQLite database itself has no built-in append-only constraint; a future hardening step could use a ledger database or hash chaining.

### Hash chaining (stretch goal)
Each audit event may include a `prev_hash = sha256(previous_event.id + previous_event.timestamp + previous_event.detail)` to enable tamper detection. Not required for MVP.

### Access controls
- The audit log is read-only via the API.
- The API does not expose an endpoint to delete or modify audit events.
- Direct database access is limited to the backend process.
