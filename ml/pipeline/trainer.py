import os

from transformers import (
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
)

from pipeline.wandb_tracker import is_enabled as wandb_enabled


def create_model(model_name: str = "distilbert-base-uncased", num_labels: int = 4):
    return AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=num_labels)


def _get_report_targets() -> list[str]:
    targets = ["mlflow"]
    if wandb_enabled():
        targets.append("wandb")
    return targets


def train_model(
    model,
    tokenizer,
    train_dataset,
    eval_dataset,
    compute_metrics_fn,
    output_dir: str = "./results",
    num_epochs: int = 3,
    batch_size: int = 32,
    learning_rate: float = 2e-5,
):
    os.environ.setdefault("MLFLOW_TRACKING_URI", "http://localhost:5000")
    os.environ.setdefault("MLFLOW_EXPERIMENT_NAME", "ai-news-classifier")

    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=learning_rate,
        warmup_steps=500,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1_macro",
        logging_steps=100,
        report_to=_get_report_targets(),
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        compute_metrics=compute_metrics_fn,
        processing_class=tokenizer,
    )

    trainer.train()
    return trainer
