import sys
import os
import tempfile

import numpy as np
import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from pipeline.dataset import load_ag_news, get_reference_distribution, LABEL_MAP
from pipeline.tokenizer import get_tokenizer, tokenize_dataset
from pipeline.trainer import create_model, train_model
from pipeline.metrics import compute_metrics, full_report
from pipeline.registry import log_training_run, promote_to_production
from pipeline import wandb_tracker


def main():
    use_wandb = wandb_tracker.is_enabled()
    train_config = {
        "model_name": "distilbert-base-uncased",
        "num_epochs": 3,
        "batch_size": 32,
        "learning_rate": 2e-5,
        "max_seq_length": 256,
        "dataset": "ag_news",
    }

    # W&B init first so HF Trainer can attach to the same run
    if use_wandb:
        print("Initializing W&B...")
        wandb_tracker.setup_wandb(run_name="initial-training", config=train_config)

    print("Loading AG News dataset...")
    train_ds, test_ds = load_ag_news()

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
        num_epochs=3,
        batch_size=32,
        learning_rate=2e-5,
    )

    eval_results = trainer.evaluate()
    print(f"Eval results: {eval_results}")

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

    from pipeline import hf_hub
    if hf_hub.is_enabled():
        try:
            hf_hub.push_model(model_save_dir, mlflow_run_id=run_id, metrics=metrics)
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
