import asyncio
import os
import sys
import tempfile
import uuid
from datetime import datetime, timezone

from app.config import settings

_retraining_lock = asyncio.Lock()


async def claim_retrain_slot(
    drift_report_id: uuid.UUID | None, reason: str
) -> uuid.UUID | None:
    from sqlalchemy import select
    from app.db import async_session
    from app.models.training_run import TrainingRun

    async with async_session() as db:
        running = (
            await db.execute(select(TrainingRun).where(TrainingRun.status == "running").limit(1))
        ).scalar_one_or_none()
        if running:
            print(f"Retraining already in progress ({running.id}); not claiming a new slot")
            return None

        training_run_id = uuid.uuid4()
        db.add(
            TrainingRun(
                id=training_run_id,
                mlflow_run_id="pending",
                trigger_reason=reason,
                drift_report_id=drift_report_id,
                status="running",
            )
        )
        await db.commit()
    return training_run_id


async def trigger_retraining(drift_report_id: uuid.UUID | None, reason: str, model_type: str = "A"):
    training_run_id = await claim_retrain_slot(drift_report_id, reason)
    if training_run_id is None:
        return None
    async with _retraining_lock:
        return await _execute_retrain(training_run_id, reason, model_type)


async def _execute_retrain(training_run_id: uuid.UUID, reason: str, model_type: str = "A"):
    from app.db import async_session
    from app.models.training_run import TrainingRun

    try:
        result = await asyncio.to_thread(_retrain_sync, model_type)

        async with async_session() as db:
            from sqlalchemy import select
            run = (await db.execute(
                select(TrainingRun).where(TrainingRun.id == training_run_id)
            )).scalar_one()

            run.mlflow_run_id = result["mlflow_run_id"]
            run.accuracy = result["accuracy"]
            run.f1_macro = result["f1_macro"]
            run.previous_f1 = result.get("previous_f1")
            run.model_uri = result.get("model_uri", "")
            run.completed_at = datetime.now(timezone.utc)

            from app.utils import metrics as m
            if result["deployed"]:
                run.status = "completed"
                run.deployed = True
                from app.services.classifier import classifier_service
                await classifier_service.reload()
                from app.utils.cache import flush_prediction_cache
                await flush_prediction_cache()
                m.set_model_info(classifier_service.model_version)
                m.set_model_scores(
                    classifier_service.model_version,
                    result["f1_macro"],
                    result["accuracy"],
                )
                print("New model deployed and cache flushed")
            else:
                run.status = "rejected"
                print(f"New model rejected: F1={result['f1_macro']:.4f}")

            m.retrain_runs_total.labels(status=run.status, trigger=reason).inc()
            await db.commit()
            return run

    except Exception as e:
        try:
            async with async_session() as db:
                from sqlalchemy import select
                run = (await db.execute(
                    select(TrainingRun).where(TrainingRun.id == training_run_id)
                )).scalar_one_or_none()
                if run:
                    run.status = "failed"
                    run.error_message = str(e)
                    run.completed_at = datetime.now(timezone.utc)
                    await db.commit()
        except Exception as db_err:
            print(f"Failed to update training run status: {db_err}")
        print(f"Retraining failed: {e}")
        return None


def _retrain_sync(model_type: str = "A") -> dict:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml"))

    from ml.pipeline.dataset import build_training_dataset
    from ml.pipeline.tokenizer import get_tokenizer, tokenize_dataset
    from ml.pipeline.trainer import create_model, train_model
    from ml.pipeline.metrics import compute_metrics
    from ml.pipeline.registry import log_training_run, promote_to_production
    from ml.pipeline import wandb_tracker

    import torch
    use_gpu = torch.cuda.is_available()
    max_train = None if use_gpu else 2000
    max_test = None if use_gpu else 500
    num_epochs = 3 if use_gpu else 1
    batch_size = 32 if use_gpu else 16
    n_corrections = 0

    if model_type == "B":
        from ml.pipeline.dataset import load_20_newsgroups
        train_ds, test_ds = load_20_newsgroups(max_train_samples=max_train, max_test_samples=max_test)
        hf_repo = settings.ab_model_b_hf_repo or "tron/news-khabar-b"
    else:
        from ml.pipeline.dataset import load_ag_news
        train_ds, test_ds = load_ag_news(max_train_samples=max_train, max_test_samples=max_test)
        train_ds, test_ds, n_corrections = build_training_dataset(
            max_train_samples=max_train,
            max_test_samples=max_test,
            correction_upsample=5,
            sync_db_url=settings.sync_database_url,
        )
        hf_repo = settings.hf_model_repo or "tron/news-khabar"

    retrain_config = {
        "trigger": "retrain",
        "epochs": num_epochs,
        "batch_size": batch_size,
        "learning_rate": 2e-5,
        "production_corrections": n_corrections,
        "correction_upsample": 5 if n_corrections else 0,
    }

    use_wandb = wandb_tracker.is_enabled()
    if use_wandb:
        wandb_tracker.setup_wandb(run_name="retrain-drift", config=retrain_config)
    tokenizer = get_tokenizer()

    train_tokenized = tokenize_dataset(train_ds, tokenizer)
    test_tokenized = tokenize_dataset(test_ds, tokenizer)
    train_tokenized.set_format("torch", columns=["input_ids", "attention_mask", "label"])
    test_tokenized.set_format("torch", columns=["input_ids", "attention_mask", "label"])

    model = create_model()
    output_dir = tempfile.mkdtemp()

    # HF Trainer logs live to both MLflow + W&B during training
    trainer = train_model(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_tokenized,
        eval_dataset=test_tokenized,
        compute_metrics_fn=compute_metrics,
        output_dir=output_dir,
        num_epochs=num_epochs,
        batch_size=batch_size,
        learning_rate=2e-5,
    )

    eval_results = trainer.evaluate()
    new_f1 = eval_results["eval_f1_macro"]
    new_acc = eval_results["eval_accuracy"]

    from app.services.classifier import classifier_service
    previous_f1 = getattr(classifier_service, '_last_f1', None)

    deployed = True
    if previous_f1 is not None:
        if new_f1 < previous_f1 - settings.retrain_f1_regression_tolerance:
            deployed = False

    model_save_dir = os.path.join(output_dir, "final_model")
    trainer.save_model(model_save_dir)
    tokenizer.save_pretrained(model_save_dir)

    # MLflow: register model + cross-link W&B run URL
    mlflow_run_id = "none"
    if deployed:
        from app.utils.storage import upload_directory
        upload_directory(model_save_dir, settings.minio_bucket, "production/model")

        try:
            mlflow_run_id = log_training_run(
                model=trainer.model,
                tokenizer=tokenizer,
                metrics={"accuracy": new_acc, "f1_macro": new_f1},
                params=retrain_config,
                model_dir=model_save_dir,
            )
            promote_to_production(mlflow_run_id)
        except Exception as e:
            import traceback
            print(f"MLflow logging failed: {e}")
            traceback.print_exc()

        try:
            from ml.pipeline import hf_hub
            if hf_hub.is_enabled():
                hf_hub.push_model(
                    model_save_dir,
                    repo_id=hf_repo,
                    mlflow_run_id=mlflow_run_id,
                    metrics={"accuracy": new_acc, "f1_macro": new_f1},
                )
        except Exception as e:
            print(f"HF push failed (non-fatal): {e}")

    # W&B: summary + cross-link MLflow run ID + model artifact
    if use_wandb:
        wandb_tracker.link_mlflow_run(mlflow_run_id)
        wandb_tracker.log_summary({
            "accuracy": new_acc,
            "f1_macro": new_f1,
            "deployed": deployed,
            "previous_f1": previous_f1 or 0,
            "mlflow_run_id": mlflow_run_id,
        })
        if deployed:
            wandb_tracker.log_model_artifact(model_save_dir, name="ai-news-classifier")
        wandb_tracker.finish()

    return {
        "mlflow_run_id": mlflow_run_id,
        "accuracy": new_acc,
        "f1_macro": new_f1,
        "previous_f1": previous_f1,
        "deployed": deployed,
        "model_uri": f"s3://{settings.minio_bucket}/production/model" if deployed else None,
    }
