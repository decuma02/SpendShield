"""Environment-backed application configuration.

Secrets are intentionally read at runtime and are never given repository
defaults.  Loading ``.env`` is useful for local development while the same
configuration works with deployment-provided environment variables.
"""

from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


def _csv(value: str) -> tuple[str, ...]:
    """Parse a comma-separated setting while ignoring blank entries."""

    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    database_url: str
    paypal_client_id: str
    paypal_client_secret: str
    paypal_webhook_id: str
    paypal_base_url: str
    ss_api_key: str
    ml_model_path: str
    review_threshold: float
    review_approval_ttl_minutes: int
    log_level: str
    cors_origins: tuple[str, ...]

    @classmethod
    def from_environment(cls) -> "Settings":
        """Build settings from environment variables with safe local defaults."""

        return cls(
            database_url=os.getenv("DATABASE_URL", "sqlite:///./spendshield.db"),
            paypal_client_id=os.getenv("PAYPAL_CLIENT_ID", ""),
            paypal_client_secret=os.getenv("PAYPAL_CLIENT_SECRET", ""),
            paypal_webhook_id=os.getenv("PAYPAL_WEBHOOK_ID", ""),
            paypal_base_url=os.getenv(
                "PAYPAL_BASE_URL", "https://api-m.sandbox.paypal.com"
            ),
            ss_api_key=os.getenv("SS_API_KEY", ""),
            ml_model_path=os.getenv(
                "ML_MODEL_PATH", "ml/models/isolation_forest_v1.pkl"
            ),
            review_threshold=float(os.getenv("REVIEW_THRESHOLD", "0.7")),
            review_approval_ttl_minutes=int(
                os.getenv("REVIEW_APPROVAL_TTL_MINUTES", "30")
            ),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            cors_origins=_csv(os.getenv("CORS_ORIGINS", "http://localhost:5173")),
        )


settings = Settings.from_environment()
