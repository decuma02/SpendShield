# SpendShield — ML Plan

> **Document status:** Planning phase. No implementation exists yet.

---

## 1. Objective

Provide a demonstrable, honest anomaly-detection component that flags unusual purchase proposals as a *soft signal* that supplements — but never overrides — the deterministic policy engine.

**Important limitations to state explicitly:**
- Performance figures reported here apply only to synthetic test data. They do not prove real-world fraud detection effectiveness.
- The ML model is not the final security authority. Policy engine BLOCK decisions cannot be overridden by a low ML score.
- ML is most useful for detecting patterns that rules do not explicitly cover, such as unusual combinations of merchant category, amount, and time-of-day that individually appear valid.

---

## 2. Model Choice: Isolation Forest

**Rationale:**
- Isolation Forest is well-suited to anomaly detection on tabular data without labelled fraud examples.
- It is available in scikit-learn, requires no special infrastructure, and produces scores efficiently at inference time.
- It can be trained on normal transaction data alone; anomalies are transactions that are isolated quickly in the random partitioning trees.
- Produces a continuous anomaly score, which maps naturally to the ALLOW/REVIEW decision boundary.

**Alternatives considered:**
- Local Outlier Factor: comparable quality but slower at inference on larger datasets.
- One-class SVM: more sensitive to feature scaling; Isolation Forest is more robust.
- Supervised classifier (XGBoost): requires labelled fraud data, which defeats the purpose of anomaly detection in a fresh deployment.

**Selected:** Isolation Forest (scikit-learn `IsolationForest`).

---

## 3. Feature Engineering

### Transaction-level features (per proposal)

| Feature name | Type | Description |
|---|---|---|
| `amount_usd` | float | Transaction amount normalised to USD |
| `hour_of_day` | int | Hour of request (0–23) |
| `day_of_week` | int | Day of week (0=Monday, 6=Sunday) |
| `merchant_category_encoded` | int | Label-encoded merchant category |
| `merchant_trust_level` | int | 0=unknown, 1=known, 2=trusted |
| `is_new_merchant` | int | 1 if merchant_id not seen in training data |
| `description_length` | int | Length of description in characters |

### Behavioural features (agent-session context, computed server-side)

| Feature name | Type | Description |
|---|---|---|
| `proposals_last_60min` | int | Number of proposals by this agent in the last 60 minutes |
| `total_amount_last_60min` | float | Sum of proposal amounts by this agent in the last 60 minutes |
| `proposals_last_24h` | int | Number of proposals by this agent in the last 24 hours |
| `total_amount_last_24h` | float | Sum of proposal amounts by this agent in the last 24 hours |
| `merchant_repeat_count` | int | Number of times this merchant_id was proposed by this agent in the last 24h |
| `amount_deviation_from_mean` | float | (amount - agent's 30-day mean amount) / (agent's 30-day std + 1) |

### Feature version
Model artifact stores the feature list as metadata. `MLScorer` verifies that the feature list matches at load time. If there is a mismatch, the scorer raises a configuration error at startup (not at inference time).

---

## 4. Synthetic Data Simulator

### File
`scripts/generate_synthetic_data.py`

### Design
The simulator generates synthetic users (agents), merchants, and transaction histories. It is designed to produce realistic distributions of normal behaviour and specific attack/anomaly patterns.

### Agent profiles

| Profile | Count | Behaviour |
|---|---|---|
| Regular user | 50 | 1–5 purchases/day, amounts $10–$200, normal hours (8am–10pm), known merchants |
| Infrequent user | 20 | <1 purchase/day, amounts $20–$150, broad hours |
| Business user | 10 | 3–15 purchases/day, amounts $50–$500, business hours, mostly known merchants |
| Anomalous agent | 5 | Generated with attack patterns (see below) |

### Merchant pool
- 30 "known and trusted" merchants across 5 categories: grocery, electronics, travel, software, retail.
- 10 "known but not trusted" merchants.
- 20 "unknown" merchants (new, not in trust list).

### Transaction categories

| Category label | Count | Generation rules |
|---|---|---|
| NORMAL | 8,000 | Agent profiles above; amounts within normal range; normal hours |
| UNUSUAL_AMOUNT | 500 | Single transaction 5–10x the agent's recent mean |
| BURST | 300 | 6–10 proposals within 20 minutes from one agent |
| STRUCTURING | 200 | 5–8 proposals at $90–$99 (just below a $100 cap) within 1 hour |
| NEW_MERCHANT_HIGH_AMOUNT | 200 | First-time merchant, amount >$300 |
| OFF_HOURS | 200 | Transactions between 2am–5am |
| REPEAT_MERCHANT | 100 | Same merchant 5+ times in 1 hour |

Total: ~9,500 records. Hold out 20% (1,900) for evaluation (stratified by category). Use remaining 7,600 as the training set (NORMAL transactions only for unsupervised training; anomalous categories withheld from the training set).

### Output format
CSV with columns matching the feature list above, plus `label` column (NORMAL / anomaly category name) for evaluation purposes. The model is trained on the feature columns only (no label). Labels are used only in the evaluation script.

---

## 5. Training Pipeline

### File
`scripts/train_model.py`

### Steps
1. Load `data/synthetic_transactions.csv` (NORMAL rows only for training).
2. Extract feature columns, impute any missing values with column medians.
3. Fit `sklearn.preprocessing.StandardScaler` on training features.
4. Fit `sklearn.ensemble.IsolationForest(n_estimators=200, contamination=0.05, random_state=42)` on scaled training features.
5. Save scaler and model together as a single artifact: `ml/models/isolation_forest_v1.pkl` (pickle or joblib).
6. Save feature list, scaler parameters, and training date in `ml/models/model_metadata.json`.

### Contamination parameter
`contamination=0.05` sets the expected fraction of anomalies in the training data. Since we train on NORMAL-only data, this controls the scoring threshold. Tune this if evaluation shows too many false positives.

---

## 6. Inference Service

### File
`backend/app/ml/scorer.py`

### Class: `MLScorer`

```
MLScorer
  __init__(model_path: str)
    Load model artifact from model_path.
    Verify feature list against model_metadata.json.
    Set self._available = True.
    On any exception: set self._available = False, log warning.

  score(proposal: ProposalSchema) -> float
    If not self._available: return 0.5 (neutral score)
    Extract feature vector from proposal + behavioural context.
    Scale features using loaded scaler.
    Call model.decision_function(features) → raw anomaly score.
    Normalise to [0.0, 1.0]:
      raw scores range from negative (normal) to positive (anomalous).
      Apply sigmoid or min-max normalisation based on training distribution.
    Return normalised score.
    On any inference exception: return 0.5, log warning.
```

### Normalisation note
`IsolationForest.decision_function` returns negative values for inliers (normal) and values near 0 or positive for anomalies. The exact range depends on `contamination` and training data. During training, record the 1st and 99th percentile of decision_function output on the training set. Use these as min/max for clipped linear normalisation at inference time.

### Risk score to decision mapping

| Normalised score | Decision contribution |
|---|---|
| 0.0 – 0.49 | Supports ALLOW |
| 0.50 – 0.69 | Neutral (ALLOW if policy allows) |
| 0.70 – 1.0 | Triggers REVIEW (if policy would ALLOW) |

The `REVIEW_THRESHOLD` (default 0.7) is configurable via environment variable.

### Model unavailability
If the model file is missing or fails to load:
- `MLScorer._available = False`.
- `score()` returns 0.5.
- Decision coordinator treats 0.5 as below the 0.7 review threshold → ALLOW.
- This is logged as a WARNING at every inference call.
- An alert in the dashboard (stretch goal) warns that ML scoring is unavailable.

**Critical:** Model unavailability does NOT bypass the policy engine. Hard rules are enforced regardless of whether the ML model is available.

---

## 7. Evaluation Methodology

### File
`scripts/evaluate_model.py`

### Three configurations compared

| Configuration | What it uses |
|---|---|
| Rules-only | Policy engine rules P-01 to P-08 only; no ML |
| Rules + aggregate limits | Rules P-01 to P-08 with rolling-window aggregate (P-02, P-03) |
| Rules + ML | Rules P-01 to P-08 + Isolation Forest scoring |

### Metrics

| Metric | Definition |
|---|---|
| Detection rate (recall) | Fraction of anomalous scenarios correctly flagged (BLOCK or REVIEW) |
| False-positive rate | Fraction of NORMAL scenarios incorrectly flagged as BLOCK or REVIEW |
| Precision | Fraction of flagged scenarios that are genuinely anomalous |
| Detection delay | Number of transactions in a sequence before first flag (for structuring scenarios) |

### Evaluation scenarios (held-out)

The 20% hold-out set (1,900 records) is used. Additionally, the eight demo scenarios defined in PROJECT_PLAN.md are run as named test cases. All evaluation is performed offline using the scripts; it is not executed at runtime.

### Expected comparison findings (hypothesis — not a guarantee)
- Rules-only: high detection rate for amount violations and block-list hits; zero detection for unusual patterns not covered by explicit rules.
- Rules + aggregate limits: additionally catches structuring and burst patterns deterministically.
- Rules + ML: additionally catches unusual-merchant-category combinations and off-hours transactions that rules do not explicitly cover; may introduce some false positives on edge-case NORMAL transactions.

### Reporting
Evaluation script prints a markdown table to stdout. Results are manually pasted into the "Evaluation Results" section below (to be filled during implementation).

---

## 8. Evaluation Results (to be completed on Day 21)

> This section will be filled in during implementation. Do not fabricate results.

| Configuration | Detection Rate | False Positive Rate | Precision |
|---|---|---|---|
| Rules-only | TBD | TBD | TBD |
| Rules + aggregate limits | TBD | TBD | TBD |
| Rules + ML | TBD | TBD | TBD |

**Caveats (must appear in any demo or presentation):**
- All figures are based on synthetic data generated by the same simulator used to train the model. This creates optimistic results compared to real-world performance.
- The simulator's attack patterns are known to the evaluation; in production, novel attacks would not match the training distribution.
- These results demonstrate that the system functions as designed; they do not prove it would detect real financial fraud.

---

## 9. Model and Feature Versioning

- Model artifact filename includes version: `isolation_forest_v1.pkl`.
- `model_metadata.json` includes: `model_version`, `feature_list`, `training_date`, `contamination`, `n_estimators`, `scaler_type`.
- Every decision record stores `ml_model_version` from the metadata.
- When the model is retrained, increment the version number in the filename and metadata.
- The backend loads the model specified by the `ML_MODEL_PATH` environment variable. Changing this variable and restarting switches to a new model version.

---

## 10. Hackathon Scope Constraints

The following ML work is explicitly out of scope for the 25-day timeline:

- Online/streaming model updates.
- Multiple model types or ensemble methods.
- Real-time feature store.
- Explainability methods beyond the raw risk score and feature values.
- Model monitoring and drift detection.
- Production-grade model registry.

The training and evaluation pipeline is a set of offline scripts run by the developer. It is not an automated MLOps pipeline.
