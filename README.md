# AI News Classifier — MLOps Pipeline

End-to-end MLOps demo: DistilBERT fine-tuned on AG News, served via FastAPI, with drift detection, auto-retraining, user feedback loop, MLflow registry, HF Hub push, Prometheus + Grafana monitoring.

## Stack

| Service | Port | Purpose |
|---|---|---|
| `backend` | 8000 | FastAPI — `/api/predict`, `/api/drift`, `/api/training`, `/metrics` |
| `frontend` | 3000 | Next.js UI — classify, feedback, drift monitor, training runs |
| `postgres` | 5432 | predictions, drift reports, training runs |
| `redis` | 6379 | prediction cache |
| `minio` | 9000 / 9001 | S3 artifact store (mlflow-artifacts, ai-news-models) |
| `mlflow` | 5000 | experiment tracking + model registry |
| `prometheus` | 9090 | metrics scrape |
| `grafana` | 3001 | dashboards |

## Prerequisites

- Docker + Docker Compose
- (Optional) NVIDIA GPU + CUDA for faster training
- HuggingFace account + write token → https://huggingface.co/settings/tokens
- (Optional) Weights & Biases API key → https://wandb.ai/authorize

## Configuration

Copy the example env file and fill in secrets:

```bash
cp .env.example .env
```

Required for auto-push to HF Hub (leave blank to disable):
```
HF_MODEL_REPO=tron/news-khabar
AB_MODEL_B_HF_REPO=tron/news-khabar-b
HF_TOKEN=hf_xxx
HF_PRIVATE=false
```

If `AB_MODEL_B_HF_REPO` is set, the backend loads model B from that HF repo for A/B routing. Otherwise model B falls back to a seeded-random-head variant of the base model.

Required for W&B tracking (leave blank to disable):
```
WANDB_API_KEY=<your-key>
WANDB_ENABLED=true
```

## First-time setup

```bash
# 1. Build and start everything
docker compose up -d --build

# 2. Wait for services to become healthy (~30s)
docker compose ps

# 3. Train the initial model (inside the backend container)
docker exec news-backend-1 python /app/ml/scripts/train_initial.py
```

To train or push the A/B model B separately, run:

```bash
docker exec news-backend-1 sh -c 'HF_MODEL_REPO=tron/news-khabar-b python /app/ml/scripts/train_initial.py'
```

`train_initial.py` will:
- Download AG News
- Fine-tune DistilBERT (3 epochs GPU, ~1 epoch on CPU)
- Upload weights to MinIO (`s3://ai-news-models/production/model`)
- Register a new MLflow version and promote to `Production`
- Push to Hugging Face Hub if `HF_MODEL_REPO` + `HF_TOKEN` are set
- Log W&B run with confusion matrix + per-class metrics

On every subsequent backend boot, the classifier loads from HF Hub first (cached under `~/.cache/huggingface/`), then falls back to MinIO, then to the base DistilBERT.

## Access points

| URL | What |
|---|---|
| http://localhost:3000 | main UI |
| http://localhost:3000/predict | classify + give feedback |
| http://localhost:3000/monitor | drift reports table + chart |
| http://localhost:3000/training | training run history + rollback |
| http://localhost:5000 | MLflow (Experiments → `ai-news-classifier`, Models tab) |
| http://localhost:3001 | Grafana (admin / admin) → "AI News Classifier" dashboard |
| http://localhost:9001 | MinIO console (minioadmin / minioadmin) |

## Drift simulation

The drift simulator has two subcommands. Both run inside the backend container so they can reach Postgres and the API.

### 1. Simulate distribution drift

Inject biased rows directly into `prediction_logs` so the next drift check trips the chi-square test.

```bash
# 300 Sports-biased rows at high confidence → label drift detected
docker exec news-backend-1 python /app/scripts/simulate_drift.py drift \
  --count 300 --dominant Sports

# Low-confidence rows → PageHinkley confidence drift
docker exec news-backend-1 python /app/scripts/simulate_drift.py drift \
  --count 300 --dominant Sports --low-confidence

# Skip the auto drift check after insertion
docker exec news-backend-1 python /app/scripts/simulate_drift.py drift \
  --count 300 --dominant Sports --no-check
```

After insertion, a drift check runs automatically. You can also trigger one manually:
```bash
curl -X POST http://localhost:8000/api/drift/check
```

What happens when drift is detected:
- a new `drift_reports` row is written
- `claim_retrain_slot` atomically creates a `training_runs` row with `status=running` and `trigger_reason=label_drift`
- a background task runs the retrain → uploads to MinIO → registers in MLflow → pushes to HF → reloads the classifier
- Grafana metrics `ainews_drift_detected`, `ainews_drift_label_pvalue`, `ainews_retrain_runs_total` update

Guards that prevent noise:
- If another retrain is already `running`, the drift check is skipped
- If the most recent drift report is still "unresolved" (no successful retrain since), a duplicate report is **not** created — the existing one is returned instead
- The drift window only considers predictions with `created_at > last_successful_deploy.completed_at`, so stale data from before the last retrain doesn't keep triggering

### 2. Simulate user feedback

Issues real `/predict` calls and then posts `PATCH /predictions/{id}/correct` with known-correct labels — exercises the full human-in-the-loop pipeline.

```bash
# 50 predictions, ~30% of them marked as wrong with a different correct label
docker exec news-backend-1 python /app/scripts/simulate_drift.py feedback \
  --count 50 --wrong-rate 0.3

# Lower wrong-rate simulates mostly-correct feedback
docker exec news-backend-1 python /app/scripts/simulate_drift.py feedback \
  --count 100 --wrong-rate 0.1
```

Each correction writes a `corrected_label` onto the `prediction_logs` row. On the next retrain, `ml/pipeline/dataset.py:build_training_dataset` pulls every row where `corrected_label IS NOT NULL AND model_version != 'simulated'`, upsamples them 5×, and mixes them into the AG News train split. The MLflow run records `production_corrections=N` and `correction_upsample=5` so you can see exactly how much real feedback influenced each retrain.

## Full end-to-end demo sequence

```bash
# 1. Seed some genuine user feedback
docker exec news-backend-1 python /app/scripts/simulate_drift.py feedback \
  --count 40 --wrong-rate 0.25

# 2. Inject drift
docker exec news-backend-1 python /app/scripts/simulate_drift.py drift \
  --count 300 --dominant Sports --no-check

# 3. Trigger drift check → retrain auto-starts
curl -X POST http://localhost:8000/api/drift/check

# 4. Watch the retrain
docker exec news-postgres-1 psql -U ainews -d ainews -c \
  "SELECT trigger_reason, status, f1_macro, started_at, completed_at FROM training_runs ORDER BY started_at DESC LIMIT 5;"

# 5. After completion, check MLflow version and HF push
curl -s http://localhost:8000/api/model/versions | python3 -m json.tool
```

## Cleanup & reset

```bash
# Remove only the simulated drift rows
docker exec news-postgres-1 psql -U ainews -d ainews -c \
  "DELETE FROM prediction_logs WHERE model_version='simulated';"

# Full teardown (keeps volumes)
docker compose down

# Full teardown + wipe DB, MinIO, Grafana state
docker compose down -v
```

## Rollback a bad model

MLflow keeps every registered version. To roll back:

```bash
# list versions
curl -s http://localhost:8000/api/model/versions | python3 -m json.tool

# roll back to a specific version (also updates MinIO, HF Hub, and reloads the backend)
curl -X POST http://localhost:8000/api/model/rollback/<version>
```

## Troubleshooting

**Backend says `hf:...` but model info shows 0 / blank F1 in Grafana**
Those metrics only set after a retrain completes. Run the initial training script (first-time setup step 3) or trigger one via `POST /api/training/trigger`.

**`Retrain: Yes` shown in the UI but `training_runs` has no new row**
Fixed — if this recurs, check that the backend image was rebuilt after `app/workers/drift_worker.py` or `app/services/retrainer.py` changed. `docker compose up -d --no-deps --build backend`.

**Drift p-value shows `0.0000` in the UI**
Old frontend bundle. Run `docker compose up -d --no-deps --build frontend`.

**MLflow Models page empty after a retrain**
The transformers flavor needs `torchvision`, which we don't install. The pipeline uses `mlflow.log_artifacts` + explicit `client.create_model_version` instead (`ml/pipeline/registry.py`). If a run completes with `mlflow_run_id="none"`, check the backend logs for a traceback from `log_training_run`.

**`/api/drift/check` returns `null`**
Expected when fewer than 30 predictions exist in the window since the last successful deploy. Generate traffic first:
```bash
for i in $(seq 1 50); do
  curl -s -X POST http://localhost:8000/api/predict \
    -H 'content-type: application/json' \
    -d "{\"text\":\"some article $i\"}" > /dev/null
done
```
