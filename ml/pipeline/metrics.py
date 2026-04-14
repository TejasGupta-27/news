import numpy as np
from sklearn.metrics import accuracy_score, f1_score, classification_report


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    acc = accuracy_score(labels, predictions)
    f1 = f1_score(labels, predictions, average="macro")
    return {"accuracy": acc, "f1_macro": f1}


def full_report(labels, predictions, label_names):
    return classification_report(labels, predictions, target_names=label_names, output_dict=True)
