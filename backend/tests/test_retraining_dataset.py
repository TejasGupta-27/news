import sys
from pathlib import Path

from datasets import ClassLabel, Dataset, Features, Value

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.pipeline import dataset as dataset_module


def test_build_training_dataset_casts_correction_labels_to_ag_news_schema(monkeypatch):
    ag_features = Features(
        {
            "text": Value("string"),
            "label": ClassLabel(names=["World", "Sports", "Business", "Sci/Tech"]),
        }
    )
    train_ds = Dataset.from_dict(
        {"text": ["base article"], "label": [0]},
        features=ag_features,
    )
    test_ds = Dataset.from_dict(
        {"text": ["eval article"], "label": [1]},
        features=ag_features,
    )
    corrections = Dataset.from_dict(
        {"text": ["fixed article", "another fix"], "label": [1, 3]},
    )

    monkeypatch.setattr(dataset_module, "load_ag_news", lambda *args, **kwargs: (train_ds, test_ds))
    monkeypatch.setattr(
        dataset_module,
        "load_production_corrections",
        lambda *args, **kwargs: corrections,
    )

    combined, returned_test, n_corrections = dataset_module.build_training_dataset(
        correction_upsample=2,
        sync_db_url="postgresql://example",
    )

    assert returned_test == test_ds
    assert n_corrections == 2
    assert len(combined) == 5
    assert combined.features["label"] == train_ds.features["label"]
