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
        loaded = False

        if settings.hf_model_repo:
            try:
                repo = settings.hf_model_repo
                token = settings.hf_token or None
                if "/" not in repo and token:
                    try:
                        from huggingface_hub import whoami
                        user = whoami(token=token).get("name")
                        if user:
                            repo = f"{user}/{repo}"
                    except Exception as e:
                        print(f"whoami lookup failed: {e}")

                print(f"Loading model from Hugging Face Hub: {repo}")
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    repo, token=token
                )
                self.tokenizer = AutoTokenizer.from_pretrained(repo, token=token)
                self.model_version = f"hf:{repo}"
                loaded = True
            except Exception as e:
                print(f"HF Hub load failed ({e}); falling back to MinIO")

        if not loaded:
            model_dir = tempfile.mkdtemp()
            try:
                download_directory(settings.minio_bucket, "production/model", model_dir)
                if not os.listdir(model_dir):
                    raise FileNotFoundError("No model files in MinIO")
                self.model = AutoModelForSequenceClassification.from_pretrained(model_dir)
                self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
                self.model_version = "production"
                self._model_dir = model_dir
                loaded = True
            except Exception as e:
                print(f"Could not load model from MinIO: {e}")
                print("Loading base (untrained) model from HuggingFace...")

        if not loaded:
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


class AbModelBClassifier(ClassifierService):
    """Second classifier for interleaved A/B comparisons (independent of drift tooling)."""

    def _load_model_sync(self):
        loaded = False
        repo = (settings.ab_model_b_hf_repo or "").strip()
        if repo:
            try:
                token = settings.hf_token or None
                hf_repo = repo
                if "/" not in hf_repo and token:
                    try:
                        from huggingface_hub import whoami

                        user = whoami(token=token).get("name")
                        if user:
                            hf_repo = f"{user}/{hf_repo}"
                    except Exception as e:
                        print(f"AB B whoami lookup failed: {e}")
                print(f"Loading A/B model B from Hugging Face Hub: {hf_repo}")
                self.model = AutoModelForSequenceClassification.from_pretrained(
                    hf_repo, token=token
                )
                self.tokenizer = AutoTokenizer.from_pretrained(hf_repo, token=token)
                self.model_version = f"hf:{hf_repo}"
                loaded = True
            except Exception as e:
                print(f"A/B model B HF load failed ({e}); falling back to seeded base head")
        if not loaded:
            print(
                "Loading A/B model B as base checkpoint with fixed seed (random classification head)..."
            )
            torch.manual_seed(settings.ab_model_b_init_seed)
            self.model = AutoModelForSequenceClassification.from_pretrained(
                settings.model_name, num_labels=len(settings.label_names)
            )
            self.tokenizer = AutoTokenizer.from_pretrained(settings.model_name)
            self.model_version = (
                f"ab-b:base:{settings.model_name}:seed{settings.ab_model_b_init_seed}"
            )
        self.model.to(self.device)
        self.model.eval()
        print(f"A/B model B loaded: {self.model_version}")


ab_classifier_b = AbModelBClassifier()
