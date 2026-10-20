from backend.app.config import Settings


def test_settings_load_all_environment_values(monkeypatch) -> None:
    values = {
        "DATABASE_URL": "sqlite:///./test.db",
        "PAYPAL_CLIENT_ID": "client-id",
        "PAYPAL_CLIENT_SECRET": "client-secret",
        "PAYPAL_WEBHOOK_ID": "webhook-id",
        "PAYPAL_BASE_URL": "https://paypal.example.test",
        "SS_API_KEY": "api-key",
        "ML_MODEL_PATH": "models/test.pkl",
        "REVIEW_THRESHOLD": "0.85",
        "REVIEW_APPROVAL_TTL_MINUTES": "45",
        "LOG_LEVEL": "DEBUG",
        "CORS_ORIGINS": "http://localhost:5173, https://dashboard.example.test",
    }
    for key, value in values.items():
        monkeypatch.setenv(key, value)

    settings = Settings.from_environment()

    assert settings.database_url == values["DATABASE_URL"]
    assert settings.paypal_client_id == values["PAYPAL_CLIENT_ID"]
    assert settings.paypal_client_secret == values["PAYPAL_CLIENT_SECRET"]
    assert settings.paypal_webhook_id == values["PAYPAL_WEBHOOK_ID"]
    assert settings.paypal_base_url == values["PAYPAL_BASE_URL"]
    assert settings.ss_api_key == values["SS_API_KEY"]
    assert settings.ml_model_path == values["ML_MODEL_PATH"]
    assert settings.review_threshold == 0.85
    assert settings.review_approval_ttl_minutes == 45
    assert settings.log_level == "DEBUG"
    assert settings.cors_origins == (
        "http://localhost:5173",
        "https://dashboard.example.test",
    )


def test_settings_use_non_secret_defaults(monkeypatch) -> None:
    for key in (
        "DATABASE_URL",
        "PAYPAL_CLIENT_ID",
        "PAYPAL_CLIENT_SECRET",
        "PAYPAL_WEBHOOK_ID",
        "PAYPAL_BASE_URL",
        "SS_API_KEY",
        "ML_MODEL_PATH",
        "REVIEW_THRESHOLD",
        "REVIEW_APPROVAL_TTL_MINUTES",
        "LOG_LEVEL",
        "CORS_ORIGINS",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings.from_environment()

    assert settings.database_url == "sqlite:///./spendshield.db"
    assert settings.paypal_client_id == ""
    assert settings.paypal_client_secret == ""
    assert settings.paypal_webhook_id == ""
    assert settings.ss_api_key == ""
    assert settings.review_threshold == 0.7
    assert settings.review_approval_ttl_minutes == 30
