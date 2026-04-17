from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://ainews:ainews_secret@localhost:5432/ainews"
    sync_database_url: str = "postgresql://ainews:ainews_secret@localhost:5432/ainews"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "ai-news-models"
    minio_secure: bool = False
    mlflow_tracking_uri: str = "http://localhost:5000"
    wandb_enabled: bool = True
    wandb_project: str = "ai-news-classifier"
    wandb_entity: str = ""
    model_name: str = "distilbert-base-uncased"
    hf_model_repo: str = ""
    hf_token: str = ""
    max_seq_length: int = 256
    drift_check_interval_minutes: int = 30
    drift_window_size: int = 500
    drift_pvalue_threshold: float = 0.05
    retrain_f1_regression_tolerance: float = 0.02
    cache_ttl_seconds: int = 3600
    label_names: list[str] = ["World", "Sports", "Business", "Technology"]
    # Pairwise A/B: model B HF repo (empty = same backbone as model_name with seeded random head)
    ab_model_b_hf_repo: str = ""
    ab_model_b_init_seed: int = 42
    ab_decision_epsilon: float = 0.02
    ab_feedback_refresh_interval_minutes: int = 1

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
