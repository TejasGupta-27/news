import os
import mlflow
from mlflow.tracking import MlflowClient

from pipeline import wandb_tracker


MODEL_NAME = "ai-news-classifier"


def setup_mlflow(tracking_uri: str = None):
    uri = tracking_uri or os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow.set_tracking_uri(uri)
    mlflow.set_experiment(MODEL_NAME)


def log_training_run(model, tokenizer, metrics: dict, params: dict, model_dir: str) -> str:
    setup_mlflow()
    use_wandb = wandb_tracker.is_enabled()

    with mlflow.start_run() as run:
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        mlflow.set_tag("model.task", "text-classification")
        mlflow.set_tag("model.base", "distilbert-base-uncased")

        if use_wandb:
            wandb_url = wandb_tracker.get_run_url()
            if wandb_url:
                mlflow.log_param("wandb_run_url", wandb_url)
                mlflow.set_tag("wandb.url", wandb_url)

        mlflow.log_artifacts(model_dir, artifact_path="model")

        mlflow_run_id = run.info.run_id
        model_uri = f"runs:/{mlflow_run_id}/model"

        client = MlflowClient()
        try:
            client.get_registered_model(MODEL_NAME)
        except Exception:
            client.create_registered_model(
                MODEL_NAME,
                description="DistilBERT fine-tuned on AG News (4-class text classification)",
            )

        mv = client.create_model_version(
            name=MODEL_NAME,
            source=model_uri,
            run_id=mlflow_run_id,
            description=f"accuracy={metrics.get('accuracy', 0):.4f} f1_macro={metrics.get('f1_macro', 0):.4f}",
        )
        mlflow.set_tag("registered_model_version", mv.version)
        print(f"[mlflow] registered {MODEL_NAME} version {mv.version} (run_id={mlflow_run_id})")

        if use_wandb:
            wandb_tracker.link_mlflow_run(mlflow_run_id)

        return mlflow_run_id


def get_production_model_uri() -> str | None:
    setup_mlflow()
    client = MlflowClient()
    try:
        versions = client.get_latest_versions(MODEL_NAME, stages=["Production"])
        if versions:
            return versions[0].source
    except Exception:
        pass
    try:
        versions = client.get_latest_versions(MODEL_NAME, stages=["None"])
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
            name=MODEL_NAME,
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
    mv = client.get_model_version(name=MODEL_NAME, version=version)
    client.transition_model_version_stage(
        name=MODEL_NAME,
        version=version,
        stage="Production",
        archive_existing_versions=True,
    )
    return {"version": mv.version, "run_id": mv.run_id, "source": mv.source}


def download_version_artifacts(version: str, dest_dir: str) -> str:
    import mlflow
    setup_mlflow()
    client = MlflowClient()
    mv = client.get_model_version(name=MODEL_NAME, version=version)
    local = mlflow.artifacts.download_artifacts(artifact_uri=mv.source, dst_path=dest_dir)
    return local
