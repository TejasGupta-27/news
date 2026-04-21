import os

from datasets import Dataset, concatenate_datasets, load_dataset

LABEL_MAP = {0: "World", 1: "Sports", 2: "Business", 3: "Technology"}

_LABEL_NAME_TO_ID = {name: idx for idx, name in LABEL_MAP.items()}


def load_ag_news(max_train_samples: int | None = None, max_test_samples: int | None = None):
    ds = load_dataset("ag_news")
    train_ds = ds["train"]
    test_ds = ds["test"]
    if max_train_samples:
        train_ds = train_ds.select(range(min(max_train_samples, len(train_ds))))
    if max_test_samples:
        test_ds = test_ds.select(range(min(max_test_samples, len(test_ds))))
    return train_ds, test_ds


def load_20_newsgroups(max_train_samples: int | None = None, max_test_samples: int | None = None):
    from sklearn.datasets import fetch_20newsgroups

    category_to_label = {
        "alt.atheism": "World",
        "comp.graphics": "Technology",
        "comp.os.ms-windows.misc": "Technology",
        "comp.sys.ibm.pc.hardware": "Technology",
        "comp.sys.mac.hardware": "Technology",
        "comp.windows.x": "Technology",
        "misc.forsale": "Business",
        "rec.autos": "Sports",
        "rec.motorcycles": "Sports",
        "rec.sport.baseball": "Sports",
        "rec.sport.hockey": "Sports",
        "sci.crypt": "Technology",
        "sci.electronics": "Technology",
        "sci.med": "Technology",
        "sci.space": "Technology",
        "soc.religion.christian": "World",
        "talk.politics.guns": "World",
        "talk.politics.mideast": "World",
        "talk.politics.misc": "World",
        "talk.religion.misc": "World",
    }

    def build_dataset(subset: str):
        raw = fetch_20newsgroups(subset=subset, remove=())
        texts = raw.data
        labels = []
        for target in raw.target:
            category = raw.target_names[target]
            mapped = category_to_label.get(category)
            if mapped is None:
                raise ValueError(f"Unknown 20 Newsgroups category: {category}")
            labels.append(_LABEL_NAME_TO_ID[mapped])
        ds = Dataset.from_dict({"text": texts, "label": labels})
        return ds

    train_ds = build_dataset("train")
    test_ds = build_dataset("test")
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


def load_production_corrections(sync_db_url: str | None = None) -> Dataset | None:
    import psycopg2

    url = sync_db_url or os.environ.get("SYNC_DATABASE_URL")
    if not url:
        return None

    query = """
        SELECT text, corrected_label
        FROM prediction_logs
        WHERE corrected_label IS NOT NULL
          AND model_version != 'simulated'
    """
    try:
        with psycopg2.connect(url) as conn, conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
    except Exception as e:
        print(f"[corrections] DB fetch failed: {e}")
        return None

    if not rows:
        return None

    texts = [r[0] for r in rows]
    labels = [int(r[1]) for r in rows]
    print(f"[corrections] loaded {len(rows)} production-corrected examples")
    return Dataset.from_dict({"text": texts, "label": labels})


def build_training_dataset(
    max_train_samples: int | None = None,
    max_test_samples: int | None = None,
    correction_upsample: int = 5,
    sync_db_url: str | None = None,
):
    train_ds, test_ds = load_ag_news(max_train_samples, max_test_samples)
    corrections = load_production_corrections(sync_db_url)
    if corrections is None or len(corrections) == 0:
        return train_ds, test_ds, 0

    ag_cols = set(train_ds.column_names)
    keep = ["text", "label"]
    train_ds = train_ds.remove_columns([c for c in ag_cols if c not in keep])
    corrections = corrections.cast(train_ds.features)

    upsampled = concatenate_datasets([corrections] * max(1, correction_upsample))
    combined = concatenate_datasets([train_ds, upsampled]).shuffle(seed=42)
    print(
        f"[corrections] mixed {len(corrections)} examples × {correction_upsample} upsample "
        f"into AG News ({len(train_ds)} base) → {len(combined)} total"
    )
    return combined, test_ds, len(corrections)
