import argparse
import sys
import os
import tempfile

import mlflow
import numpy as np
import torch

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def load_dotenv(path: str) -> None:
    if not os.path.exists(path):
        return
    print(f"Loading environment variables from {path}")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_dotenv(os.path.join(ROOT_DIR, ".env"))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from pipeline.dataset import (
    LABEL_MAP,
    get_reference_distribution,
    load_20_newsgroups,
    load_ag_news,
)
from pipeline.tokenizer import get_tokenizer, tokenize_dataset
from pipeline.trainer import create_model, train_model
from pipeline.metrics import compute_metrics, full_report
from pipeline.registry import log_training_run, promote_to_production
from pipeline import wandb_tracker
from pipeline import hf_hub


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--hf-model-repo",
        default=None,
        help="Optional Hugging Face repo to push this model to; overrides HF_MODEL_REPO env var",
    )
    p.add_argument(
        "--dataset",
        choices=["ag_news", "20_newsgroups"],
        default=None,
        help="Dataset to train on. If omitted, model B repos ending in '-b' default to 20_newsgroups.",
    )
    args = p.parse_args()

    hf_model_repo = args.hf_model_repo or os.environ.get("HF_MODEL_REPO")
    dataset = args.dataset
    if dataset is None:
        if hf_model_repo and hf_model_repo.endswith("-b"):
            dataset = "20_newsgroups"
        else:
            dataset = "ag_news"

    is_model_b = dataset == "20_newsgroups" or (hf_model_repo and hf_model_repo.endswith("-b"))
    train_config = {
        "model_name": "distilbert-base-uncased",
        "num_epochs": 3,
        "batch_size": 32,
        "learning_rate": 2e-5,
        "max_seq_length": 256,
        "dataset": dataset,
        "data_subset": "10%" if is_model_b else "full",
    }
    use_wandb = wandb_tracker.is_enabled()

    # W&B init first so HF Trainer can attach to the same run
    if use_wandb:
        print("Initializing W&B...")
        wandb_tracker.setup_wandb(run_name="initial-training", config=train_config)

    if dataset == "ag_news":
        print("Loading AG News dataset...")
        train_ds, test_ds = load_ag_news()
    else:
        print("Loading 20 Newsgroups dataset and mapping into 4 label buckets...")
        train_ds, test_ds = load_20_newsgroups()

    if is_model_b:
        train_limit = max(1, int(len(train_ds) * 0.1))
        test_limit = max(1, int(len(test_ds) * 0.1))
        print(f"Using 10% subset for Model B: {train_limit} train examples, {test_limit} test examples")
        train_ds = train_ds.select(range(train_limit))
        test_ds = test_ds.select(range(test_limit))

    ref_dist = get_reference_distribution(test_ds)
    print(f"Reference distribution: {ref_dist}")

    print("Loading tokenizer...")
    tokenizer = get_tokenizer()

    print("Tokenizing datasets...")
    train_tokenized = tokenize_dataset(train_ds, tokenizer)
    test_tokenized = tokenize_dataset(test_ds, tokenizer)
    train_tokenized.set_format("torch", columns=["input_ids", "attention_mask", "label"])
    test_tokenized.set_format("torch", columns=["input_ids", "attention_mask", "label"])

    print("Creating model...")
    model = create_model()

    output_dir = tempfile.mkdtemp()
    print(f"Training (output: {output_dir})...")
    # HF Trainer reports live metrics to both MLflow + W&B during training
    trainer = train_model(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_tokenized,
        eval_dataset=test_tokenized,
        compute_metrics_fn=compute_metrics,
        output_dir=output_dir,
        num_epochs=train_config["num_epochs"],
        batch_size=train_config["batch_size"],
        learning_rate=train_config["learning_rate"],
    )

    eval_results = trainer.evaluate()
    print(f"Eval results: {eval_results}")

    if mlflow.active_run() is not None:
        print("Closing leftover active MLflow run before manual logging...")
        mlflow.end_run()

    metrics = {
        "accuracy": eval_results["eval_accuracy"],
        "f1_macro": eval_results["eval_f1_macro"],
    }

    # Generate predictions for confusion matrix
    preds_output = trainer.predict(test_tokenized)
    y_pred = np.argmax(preds_output.predictions, axis=-1).tolist()
    y_true = preds_output.label_ids.tolist()
    label_names = list(LABEL_MAP.values())

    print("Saving model to MinIO...")
    from app.utils.storage import upload_directory
    model_save_dir = os.path.join(output_dir, "final_model")
    trainer.save_model(model_save_dir)
    tokenizer.save_pretrained(model_save_dir)
    upload_directory(model_save_dir, os.environ.get("MINIO_BUCKET", "ai-news-models"), "production/model")

    # MLflow: log run, register model, cross-link with W&B
    print("Logging to MLflow (+ W&B cross-link)...")
    run_id = log_training_run(
        model=trainer.model,
        tokenizer=tokenizer,
        metrics=metrics,
        params=train_config,
        model_dir=model_save_dir,
    )
    print(f"MLflow run ID: {run_id}")

    promote_to_production(run_id)
    print("Model promoted to production.")

    repo = hf_model_repo
    if repo:
        try:
            hf_hub.push_model(model_save_dir, repo_id=repo, mlflow_run_id=run_id, metrics=metrics)
        except Exception as e:
            print(f"HF push failed (non-fatal): {e}")
    else:
        print("HF push skipped (HF_MODEL_REPO / HF_TOKEN not set)")

    # W&B: log final summary, confusion matrix, model artifact, per-class metrics table
    if use_wandb:
        wandb_tracker.log_summary(metrics)
        wandb_tracker.log_confusion_matrix(y_true, y_pred, label_names)

        report = full_report(y_true, y_pred, label_names)
        table_data = []
        for cls_name in label_names:
            cls = report[cls_name]
            table_data.append([
                cls_name,
                round(cls["precision"], 4),
                round(cls["recall"], 4),
                round(cls["f1-score"], 4),
                int(cls["support"]),
            ])
        wandb_tracker.log_table(
            "per_class_metrics",
            columns=["Class", "Precision", "Recall", "F1", "Support"],
            data=table_data,
        )

        wandb_tracker.log_model_artifact(model_save_dir, name="ai-news-classifier")
        wandb_tracker.finish()
        print("W&B run complete.")

    print("Done!")


if __name__ == "__main__":
    main()
