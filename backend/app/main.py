"""FastAPI application entry point for SpendShield."""

from fastapi import FastAPI


app = FastAPI(
    title="SpendShield API",
    version="0.1.0",
    description="AI-governed payment guardrails and audit middleware.",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Return a lightweight liveness response."""

    return {"status": "ok"}
