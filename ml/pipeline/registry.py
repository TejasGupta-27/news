import os
import mlflow
from mlflow.tracking import MlflowClient

from pipeline import wandb_tracker


def setup_mlflow(tracking_uri: str = None):
    uri = tracking_uri or os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment("ai-news-classifier")


def log_training_run(model, tokenizer, metrics: dict, params: dict, model_dir: str) -> str:
    setup_mlflow()
    use_wandb = wandb_tracker.is_enabled()

    with mlflow.start_run() as run:
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)

        if use_wandb:
            wandb_url = wandb_tracker.get_run_url()
            if wandb_url:
                mlflow.log_param("wandb_run_url", wandb_url)
                mlflow.set_tag("wandb.url", wandb_url)

        mlflow.transformers.log_model(
            transformers_model={"model": model, "tokenizer": tokenizer},
            artifact_path="model",
            registered_model_name="ai-news-classifier",
        )

        mlflow_run_id = run.info.run_id

        if use_wandb:
            wandb_tracker.link_mlflow_run(mlflow_run_id)

        return mlflow_run_id


def get_production_model_uri() -> str | None:
    setup_mlflow()
    client = MlflowClient()
    try:
        versions = client.get_latest_versions("ai-news-classifier", stages=["Production"])
        if versions:
            return versions[0].source
    except Exception:
        pass
    try:
        versions = client.get_latest_versions("ai-news-classifier", stages=["None"])
        if versions:
            return versions[0].source
    except Exception:
        pass
    return None


def promote_to_production(run_id: str):
    setup_mlflow()
    client = MlflowClient()
    versions = client.search_model_versions(f"run_id='{run_id}'")
    if versions:
        client.transition_model_version_stage(
            name="ai-news-classifier",
            version=versions[0].version,
            stage="Production",
        )


def list_model_versions() -> list[dict]:
    setup_mlflow()
    client = MlflowClient()
    versions = client.search_model_versions("name='ai-news-classifier'")
    return [
        {
            "version": v.version,
            "run_id": v.run_id,
            "stage": v.current_stage,
            "source": v.source,
            "creation_timestamp": v.creation_timestamp,
        }
        for v in sorted(versions, key=lambda x: int(x.version), reverse=True)
    ]


def promote_version_to_production(version: str) -> dict:
    setup_mlflow()
    client = MlflowClient()
    mv = client.get_model_version(name="ai-news-classifier", version=version)
    client.transition_model_version_stage(
        name="ai-news-classifier",
        version=version,
        stage="Production",
        archive_existing_versions=True,
    )
    return {"version": mv.version, "run_id": mv.run_id, "source": mv.source}


def download_version_artifacts(version: str, dest_dir: str) -> str:
    import mlflow
    setup_mlflow()
    client = MlflowClient()
    mv = client.get_model_version(name="ai-news-classifier", version=version)
    local = mlflow.artifacts.download_artifacts(artifact_uri=mv.source, dst_path=dest_dir)
    return local
