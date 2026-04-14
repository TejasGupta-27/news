import asyncio
import os
import tempfile

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.config import settings
from app.utils.storage import download_directory


class ClassifierService:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.model_version = "none"
        self.model_name = settings.model_name
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model_dir = None

    async def load_model(self):
        await asyncio.to_thread(self._load_model_sync)

    def _load_model_sync(self):
        model_dir = tempfile.mkdtemp()
        try:
            download_directory(settings.minio_bucket, "production/model", model_dir)
            files = os.listdir(model_dir)
            if not files:
                raise FileNotFoundError("No model files in MinIO")
        except Exception as e:
            print(f"Could not load model from MinIO: {e}")
            print("Loading base model from HuggingFace...")
            model_dir = None

        if model_dir:
            self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
            self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
            self.model_version = "production"
            self._model_dir = model_dir
        else:
            self.model = AutoModelForSequenceClassification.from_pretrained(
                settings.model_name, num_labels=4
            )
            self.tokenizer = AutoTokenizer.from_pretrained(settings.model_name)
            self.model_version = "base-untrained"

        self.model.to(self.device)
        self.model.eval()
        print(f"Model loaded: {self.model_version}")

    def predict(self, text: str) -> dict:
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding="max_length",
            truncation=True,
            max_length=settings.max_seq_length,
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.softmax(outputs.logits, dim=-1)[0]

        label_id = torch.argmax(probs).item()
        label_name = settings.label_names[label_id]
        confidence = probs[label_id].item()
        probabilities = {name: probs[i].item() for i, name in enumerate(settings.label_names)}

        return {
            "label": label_name,
            "label_id": label_id,
            "confidence": confidence,
            "probabilities": probabilities,
        }

    async def reload(self):
        await asyncio.to_thread(self._load_model_sync)


classifier_service = ClassifierService()
