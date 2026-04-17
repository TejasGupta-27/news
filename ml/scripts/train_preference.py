"""
Train a preference classifier P(A preferred | x, summary(y_A), summary(y_B)).

Requires real pairwise feedback only: save GET /api/ab/export and pass --feedback_file.
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

import numpy as np
import torch
from sklearn.metrics import accuracy_score, roc_auc_score
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

from pipeline.preference_dataset import load_pairwise_feedback_file


def _tokenize(batch, tokenizer):
    pairs = [
        f"{sa}{tokenizer.sep_token}{sb}"
        for sa, sb in zip(batch["summary_a"], batch["summary_b"])
    ]
    enc = tokenizer(
        batch["text"],
        pairs,
        truncation=True,
        max_length=512,
        padding="max_length",
    )
    enc["labels"] = batch["label"]
    return enc


def main():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--feedback_file",
        type=str,
        required=True,
        help="JSON array or JSONL from /api/ab/export (completed rows with human labels only)",
    )
    p.add_argument("--model_name", type=str, default="distilbert-base-uncased")
    p.add_argument("--output_dir", type=str, default="./preference_model_out")
    p.add_argument("--epochs", type=int, default=2)
    p.add_argument("--batch_size", type=int, default=16)
    p.add_argument("--lr", type=float, default=2e-5)
    args = p.parse_args()

    ds = load_pairwise_feedback_file(args.feedback_file)
    ds = ds.train_test_split(test_size=0.15, seed=42)
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)

    def tok_fn(batch):
        return _tokenize(batch, tokenizer)

    train_t = ds["train"].map(tok_fn, batched=True, remove_columns=ds["train"].column_names)
    eval_t = ds["test"].map(tok_fn, batched=True, remove_columns=ds["test"].column_names)
    train_t.set_format("torch", columns=["input_ids", "attention_mask", "labels"])
    eval_t.set_format("torch", columns=["input_ids", "attention_mask", "labels"])

    model = AutoModelForSequenceClassification.from_pretrained(args.model_name, num_labels=2)

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        pred = np.argmax(logits, axis=-1)
        probs = torch.softmax(torch.tensor(logits), dim=-1)[:, 1].numpy()
        out = {"accuracy": accuracy_score(labels, pred)}
        try:
            out["roc_auc"] = float(roc_auc_score(labels, probs))
        except ValueError:
            out["roc_auc"] = 0.0
        return out

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="roc_auc",
        logging_steps=50,
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_t,
        eval_dataset=eval_t,
        processing_class=tokenizer,
        compute_metrics=compute_metrics,
    )
    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"Saved preference model to {args.output_dir}")


if __name__ == "__main__":
    main()
