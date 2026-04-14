from datasets import load_dataset

LABEL_MAP = {0: "World", 1: "Sports", 2: "Business", 3: "Technology"}


def load_ag_news(max_train_samples: int | None = None, max_test_samples: int | None = None):
    ds = load_dataset("ag_news")
    train_ds = ds["train"]
    test_ds = ds["test"]
    if max_train_samples:
        train_ds = train_ds.select(range(min(max_train_samples, len(train_ds))))
    if max_test_samples:
        test_ds = test_ds.select(range(min(max_test_samples, len(test_ds))))
    return train_ds, test_ds


def get_label_name(label_id: int) -> str:
    return LABEL_MAP[label_id]


def get_reference_distribution(test_ds) -> dict[str, float]:
    from collections import Counter
    counts = Counter(test_ds["label"])
    total = sum(counts.values())
    return {LABEL_MAP[k]: counts[k] / total for k in sorted(counts.keys())}
