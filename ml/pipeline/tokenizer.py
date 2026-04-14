from transformers import AutoTokenizer

DEFAULT_MODEL = "distilbert-base-uncased"
MAX_LENGTH = 256


def get_tokenizer(model_name: str = DEFAULT_MODEL):
    return AutoTokenizer.from_pretrained(model_name)


def tokenize_dataset(dataset, tokenizer, max_length: int = MAX_LENGTH):
    def _tokenize(batch):
        return tokenizer(batch["text"], padding="max_length", truncation=True, max_length=max_length)

    return dataset.map(_tokenize, batched=True, remove_columns=["text"])
