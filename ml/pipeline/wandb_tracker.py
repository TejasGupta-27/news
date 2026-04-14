import os

import wandb


def setup_wandb(
    project: str = None,
    entity: str = None,
    run_name: str = None,
    config: dict = None,
    mlflow_run_id: str = None,
):
    project = project or os.environ.get("WANDB_PROJECT", "ai-news-classifier")
    entity = entity or os.environ.get("WANDB_ENTITY", None)

    tags = []
    if mlflow_run_id:
        tags.append(f"mlflow:{mlflow_run_id}")

    run_config = config or {}
    if mlflow_run_id:
        run_config["mlflow_run_id"] = mlflow_run_id
    run_config["mlflow_tracking_uri"] = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5000")

    wandb.init(
        project=project,
        entity=entity or None,
        name=run_name,
        config=run_config,
        tags=tags,
        reinit=True,
    )


def link_mlflow_run(mlflow_run_id: str):
    if wandb.run:
        wandb.run.config.update({"mlflow_run_id": mlflow_run_id}, allow_val_change=True)
        wandb.run.tags = list(wandb.run.tags or []) + [f"mlflow:{mlflow_run_id}"]
        wandb.run.notes = f"MLflow run: {mlflow_run_id}"


def log_metrics(metrics: dict, step: int = None):
    wandb.log(metrics, step=step)


def log_summary(metrics: dict):
    for k, v in metrics.items():
        wandb.run.summary[k] = v


def log_confusion_matrix(y_true: list, y_pred: list, class_names: list):
    wandb.log({
        "confusion_matrix": wandb.plot.confusion_matrix(
            y_true=y_true,
            preds=y_pred,
            class_names=class_names,
        )
    })


def log_model_artifact(model_dir: str, name: str = "model"):
    artifact = wandb.Artifact(name, type="model")
    artifact.add_dir(model_dir)
    wandb.log_artifact(artifact)


def log_table(name: str, columns: list[str], data: list[list]):
    table = wandb.Table(columns=columns, data=data)
    wandb.log({name: table})


def get_run_url() -> str | None:
    if wandb.run:
        return wandb.run.get_url()
    return None


def finish():
    wandb.finish()


def is_enabled() -> bool:
    enabled = os.environ.get("WANDB_ENABLED", "true").lower()
    api_key = os.environ.get("WANDB_API_KEY", "")
    return enabled == "true" and len(api_key) > 0
