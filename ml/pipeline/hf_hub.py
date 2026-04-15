import os
import tempfile

from huggingface_hub import HfApi, create_repo, login, whoami
from transformers import AutoModelForSequenceClassification, AutoTokenizer


LABEL_NAMES = ["World", "Sports", "Business", "Technology"]


def _get_token() -> str | None:
    return (
        os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGINGFACE_TOKEN")
        or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    )


def is_enabled() -> bool:
    return bool(os.environ.get("HF_MODEL_REPO") and _get_token())


def push_model(
    model_dir: str,
    repo_id: str | None = None,
    private: bool = False,
    mlflow_run_id: str | None = None,
    metrics: dict | None = None,
) -> str | None:
    repo = repo_id or os.environ.get("HF_MODEL_REPO")
    token = _get_token()
    if not repo or not token:
        print("HF_MODEL_REPO or HF_TOKEN not set - skipping HF push")
        return None

    private_env = os.environ.get("HF_PRIVATE", "").lower() in ("1", "true", "yes")
    private = private or private_env

    login(token=token, add_to_git_credential=False)

    if "/" not in repo:
        try:
            user = whoami(token=token).get("name")
            if user:
                repo = f"{user}/{repo}"
                print(f"[HF] Resolved bare name to {repo}")
        except Exception as e:
            print(f"[HF] Could not resolve namespace via whoami: {e}")

    print(f"[HF] Loading model from {model_dir}")
    model = AutoModelForSequenceClassification.from_pretrained(model_dir)
    tokenizer = AutoTokenizer.from_pretrained(model_dir)

    id2label = {i: name for i, name in enumerate(LABEL_NAMES)}
    label2id = {v: k for k, v in id2label.items()}
    model.config.id2label = id2label
    model.config.label2id = label2id

    print(f"[HF] Ensuring repo {repo} (private={private})")
    create_repo(repo_id=repo, token=token, private=private, exist_ok=True)

    commit_msg_parts = ["Update model"]
    if mlflow_run_id:
        commit_msg_parts.append(f"mlflow_run={mlflow_run_id}")
    if metrics:
        commit_msg_parts.append(
            "metrics=" + ",".join(f"{k}={v:.4f}" for k, v in metrics.items() if isinstance(v, (int, float)))
        )
    commit_message = " | ".join(commit_msg_parts)

    print(f"[HF] Pushing model + tokenizer to {repo} ({commit_message})")
    model.push_to_hub(repo, token=token, commit_message=commit_message)
    tokenizer.push_to_hub(repo, token=token, commit_message=commit_message)

    readme = (
        f"# {repo}\n\nDistilBERT fine-tuned on AG News (4 classes: {', '.join(LABEL_NAMES)})."
        " Auto-pushed from the ai-news-classifier training pipeline.\n"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(readme)
        readme_path = f.name
    try:
        HfApi().upload_file(
            path_or_fileobj=readme_path,
            path_in_repo="README.md",
            repo_id=repo,
            token=token,
        )
    finally:
        os.unlink(readme_path)

    url = f"https://huggingface.co/{repo}"
    print(f"[HF] Push complete: {url}")
    return url
