import argparse
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

from huggingface_hub import HfApi, create_repo, login
from transformers import AutoModelForSequenceClassification, AutoTokenizer


def _resolve_model_dir(local_dir: str | None) -> str:
    if local_dir and os.path.isdir(local_dir) and os.listdir(local_dir):
        return local_dir

    from app.config import settings
    from app.utils.storage import download_directory

    target = tempfile.mkdtemp()
    print(f"Downloading model from MinIO ({settings.minio_bucket}/production/model) -> {target}")
    download_directory(settings.minio_bucket, "production/model", target)
    if not os.listdir(target):
        raise FileNotFoundError("No model files found in MinIO at production/model")
    return target


def push(repo_id: str, local_dir: str | None, private: bool, token: str | None):
    hf_token = token or os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if not hf_token:
        raise RuntimeError("Set HF_TOKEN env var (or pass --token). Create one at https://huggingface.co/settings/tokens")

    login(token=hf_token, add_to_git_credential=False)

    model_dir = _resolve_model_dir(local_dir)

    print(f"Loading model from {model_dir}")
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    tokenizer = AutoTokenizer.from_pretrained(model_dir)

    id2label = {0: "World", 1: "Sports", 2: "Business", 3: "Technology"}
    label2id = {v: k for k, v in id2label.items()}
    model.config.id2label = id2label
    model.config.label2id = label2id

    print(f"Creating/ensuring repo {repo_id} (private={private})")
    create_repo(repo_id=repo_id, token=hf_token, private=private, exist_ok=True)

    print(f"Pushing model + tokenizer to {repo_id}")
    model.push_to_hub(repo_id, token=hf_token)
    tokenizer.push_to_hub(repo_id, token=hf_token)

    api = HfApi()
    readme = (
        f"# {repo_id}\n\nDistilBERT fine-tuned on AG News (4 classes: World, Sports, Business, Technology)."
        " Auto-pushed from the ai-news-classifier pipeline.\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(readme)
        readme_path = f.name
    api.upload_file(
        path_or_fileobj=readme_path,
        path_in_repo="README.md",
        repo_id=repo_id,
        token=hf_token,
    )
    os.unlink(readme_path)

    print(f"Done: https://huggingface.co/{repo_id}")


def main():
    parser = argparse.ArgumentParser(description="Push trained model to Hugging Face Hub")
    parser.add_argument("--repo", required=True, help="e.g. yourname/ai-news-classifier")
    parser.add_argument("--local-dir", default=None, help="Local model dir (else pulls from MinIO)")
    parser.add_argument("--private", action="store_true")
    parser.add_argument("--token", default=None)
    args = parser.parse_args()

    push(args.repo, args.local_dir, args.private, args.token)


if __name__ == "__main__":
    main()
