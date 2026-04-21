# Grafana Multi-Model Monitoring Setup

## ✅ Code Changes Completed

Your metrics now support multiple models with proper labels:

### Changed Metrics:
1. **prediction_latency** - Now labeled by `model_version`
   - Before: `ainews_prediction_latency_seconds`
   - After: `ainews_prediction_latency_seconds{model_version="hf:Tron2703/new-khabar"}`

2. **prediction_confidence** - Now labeled by `model_version`
   - Before: `ainews_prediction_confidence`
   - After: `ainews_prediction_confidence{model_version="hf:Tron2703/new-khabar-b"}`

3. **drift_label_pvalue** - Now labeled by `model_version`
4. **drift_confidence_score** - Now labeled by `model_version`
5. **drift_detected** - Now labeled by `model_version`
6. **drift_checks_total** - Now labeled by both `outcome` and `model_version`

### Files Modified:
- ✅ `backend/app/utils/metrics.py` - Added model_version labels to metrics
- ✅ `backend/app/routers/predict.py` - Uses model labels when recording latency & confidence
- ✅ `backend/app/workers/drift_worker.py` - Uses model labels when recording drift metrics

---

## 🎨 Grafana Dashboard Changes (Do This Next)

After restarting the backend, configure Grafana with a dropdown variable:

### Step 1: Add a Model Variable to Your Dashboard

1. Go to **⚙️ Dashboard Settings** (top right)
2. Click **Variables**
3. Click **New variable**
4. Fill in:
   ```
   Name:             model
   Type:             Query
   Data source:      Prometheus
   Query:            label_values(ainews_prediction_latency_seconds, model_version)
   Refresh:          On Time Range Change
   Selection:        Multi-value (optional)
   Include all:      Check this box
   ```
5. Click **Create** → **Save**

### Step 2: Update All Panel Queries

For **each panel** in your dashboard, update the query to use `$model`:

#### Example 1: Prediction Latency Panel
**Old Query:**
```promql
rate(ainews_prediction_latency_seconds_sum[5m]) / rate(ainews_prediction_latency_seconds_count[5m])
```

**New Query:**
```promql
rate(ainews_prediction_latency_seconds_sum{model_version=~"$model"}[5m]) / rate(ainews_prediction_latency_seconds_count{model_version=~"$model"}[5m])
```

#### Example 2: Drift Detection Panel
**Old Query:**
```promql
ainews_drift_detected
```

**New Query:**
```promql
ainews_drift_detected{model_version=~"$model"}
```

#### Example 3: Prediction Confidence Panel
**Old Query:**
```promql
rate(ainews_prediction_confidence_sum[5m]) / rate(ainews_prediction_confidence_count[5m])
```

**New Query:**
```promql
rate(ainews_prediction_confidence_sum{model_version=~"$model"}[5m]) / rate(ainews_prediction_confidence_count{model_version=~"$model"}[5m])
```

#### Example 4: Drift P-Value Panel
**Old Query:**
```promql
ainews_drift_label_pvalue
```

**New Query:**
```promql
ainews_drift_label_pvalue{model_version=~"$model"}
```

#### Example 5: Predictions Total Panel
**Old Query (already has model_version):**
```promql
rate(ainews_predictions_total[5m])
```

**Update to:**
```promql
rate(ainews_predictions_total{model_version=~"$model"}[5m])
```

### Step 3: Save & Test

1. Click **Save** on the dashboard
2. At the top, you should see a dropdown: **model**
3. Select models to compare:
   - ✅ All Models
   - ✅ hf:Tron2703/new-khabar
   - ✅ hf:Tron2703/new-khabar-b
4. All graphs will update dynamically

---

## 🚀 Deployment Steps

### 1. Restart Backend to Apply Code Changes
```bash
# In your project root
docker compose restart backend

# or full rebuild
docker compose up -d --build backend
```

### 2. Wait for Metrics to Appear in Prometheus
- Go to http://localhost:9090
- Query: `ainews_prediction_latency_seconds`
- You should see labels with different model versions

### 3. Update Grafana Dashboards
- Go to http://localhost:3001 (admin / admin)
- Edit your existing dashboard
- Add the `$model` variable (Step 1 above)
- Update all panel queries (Step 2 above)
- Save the dashboard

### 4. Verify It Works
- Make predictions with both models (if A/B routing is enabled)
- Check Grafana - toggle between models using the dropdown
- Graphs should update accordingly

---

## 🎯 Quick Reference: Query Pattern

For **any metric**, use this pattern:

```promql
{metric_name}{model_version=~"$model"}
```

Common metrics:
- `ainews_prediction_latency_seconds`
- `ainews_prediction_confidence`
- `ainews_predictions_total`
- `ainews_drift_label_pvalue`
- `ainews_drift_confidence_score`
- `ainews_drift_detected`
- `ainews_drift_checks_total`

---

## ✨ Result

After these changes, your Grafana dashboard will:
- ✅ Show metrics for both `new-khabar` and `new-khabar-b`
- ✅ Allow switching between models with a dropdown
- ✅ Display latency, drift, confidence, and cache metrics per model
- ✅ Enable side-by-side comparison of model performance

No need to duplicate dashboards. One dashboard, multiple views. 🎉
