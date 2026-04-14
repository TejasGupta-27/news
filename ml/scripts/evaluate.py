import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.dataset import load_ag_news, LABEL_MAP
from pipeline.tokenizer import get_tokenizer, tokenize_dataset
from pipeline.metrics import full_report
from transformers import AutoModelForSequenceClassification
import torch
import numpy as np


def main(model_path: str):
    _, test_ds = load_ag_news()
    tokenizer = get_tokenizer()
    test_tokenized = tokenize_dataset(test_ds, tokenizer)
    test_tokenized.set_format("torch", columns=["input_ids", "attention_mask", "label"])

    model = AutoModelForSequenceClassification.from_pretrained(model_path)
    model.eval()

    all_preds = []
    all_labels = []

    for i in range(0, len(test_tokenized), 64):
        batch = test_tokenized[i : i + 64]
        with torch.no_grad():
            outputs = model(
                input_ids=batch["input_ids"],
                attention_mask=batch["attention_mask"],
            )
        preds = torch.argmax(outputs.logits, dim=-1).numpy()
        all_preds.extend(preds.tolist())
        all_labels.extend(batch["label"].numpy().tolist())

    report = full_report(all_labels, all_preds, list(LABEL_MAP.values()))
    for cls_name, metrics in report.items():
        if isinstance(metrics, dict):
            print(f"{cls_name}: precision={metrics.get('precision', 0):.4f} recall={metrics.get('recall', 0):.4f} f1={metrics.get('f1-score', 0):.4f}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "./results/final_model"
    main(path)
