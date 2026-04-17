# Quick Start Guide - Fixed Predict Route

## Prerequisites
- Docker & Docker Compose installed
- Node.js 20+ installed locally
- Port 3000 (frontend) and 8000 (backend) available

## Option 1: Docker Compose (Recommended)

### Start All Services
```bash
cd /home/abhay/Documents/news
docker-compose up
```

Wait for all services to be healthy (1-2 minutes).

### Access the Application
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Metrics: http://localhost:8000/metrics
- Grafana: http://localhost:3001 (admin/admin)
- MLFlow: http://localhost:5000

## Option 2: Local Development (Faster Iteration)

### 1. Start Backend Services
```bash
cd /home/abhay/Documents/news
docker-compose up postgres redis minio mlflow prometheus grafana
```

### 2. Start Backend API
```bash
cd backend
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r pyproject.toml

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Start Frontend
In a new terminal:
```bash
cd frontend
npm install
npm run dev
```

Access at http://localhost:3000

## Testing the Fixes

### Test 1: Basic Prediction (No Explanation)
1. Go to http://localhost:3000/predict
2. Paste this sample text:
   ```
   Apple announced a new iPhone today that features an improved camera system 
   and faster processor, signaling the company's continued focus on photography 
   and performance in the smartphone market.
   ```
3. Make sure "Include explanations" is OFF
4. Click "Classify"
5. **Expected**: Prediction appears in ~1-2 seconds, likely "Technology"

### Test 2: Prediction with Explanation
1. Clear the form
2. Paste the same text or different article
3. Toggle ON "Include explanations (slower)"
4. Click "Classify"
5. **Expected**: Prediction + token attributions appear in ~5-10 seconds

### Test 3: Toggle Functionality
1. Make a prediction without explanation (keep the result showing)
2. Toggle ON "Include explanations"
3. **Expected**: The result should disappear, prompting you to re-classify
4. Click "Classify" again with the same text
5. **Expected**: Same prediction but now with explanations

### Test 4: Error Handling
1. Stop the backend service
2. Try to make a prediction
3. **Expected**: Clear error message "Could not connect to backend. Is it running?"

### Test 5: Feedback Widget
1. Make any prediction
2. Scroll down and see the feedback widget
3. Click "Yes" if prediction is correct
4. **Expected**: Confirmation message appears

## Backend Health Checks

### Check API is Running
```bash
curl http://localhost:8000/api/health
# Response: {"status":"ok"}
```

### Check Model is Loaded
```bash
curl http://localhost:8000/api/model/info
# Response: {"version":"...","loaded":true,"model_name":"distilbert-base-uncased"}
```

### Test Prediction Endpoint
```bash
curl -X POST http://localhost:8000/api/predict \
  -H "Content-Type: application/json" \
  -d '{"text":"This is a test article about technology and AI.","explain":false}'
```

## Troubleshooting

### Issue: "Is the backend running?" error
**Solution**:
1. Check if backend service is running: `curl http://localhost:8000/api/health`
2. Check backend logs: `docker-compose logs backend`
3. Ensure ports 8000 isn't blocked
4. Check `NEXT_PUBLIC_API_URL` env variable

### Issue: Model Takes Too Long to Load
**Symptoms**: First request times out after 60 seconds
**Reason**: Model downloading from HuggingFace Hub (first time only)
**Solution**: Wait 2-3 minutes for initial load, subsequent requests will be fast

### Issue: Out of Memory
**Symptoms**: Backend crashes with OOM error
**Solution**: 
- Reduce model size: change `model_name` in .env to `distilbert-base-uncased`
- Allocate more memory to Docker: Settings > Resources > Memory

### Issue: Explanation Generation is Slow
**Symptoms**: Predictions with explanation take >30 seconds
**Reason**: transformers_interpret uses attention maps (CPU intensive)
**Solution**: Normal behavior, GPU would improve but not critical for demo

### Issue: Redis Connection Error
**Symptoms**: "ConnectionError" in logs
**Solution**: 
- Check redis is running: `docker-compose ps`
- Restart redis: `docker-compose restart redis`

### Issue: Port Already in Use
**Solutions**:
- Change port in docker-compose.yml
- Or kill process using the port:
  ```bash
  # macOS/Linux
  sudo lsof -ti:3000 | xargs kill -9
  
  # Windows
  netstat -ano | findstr :3000
  taskkill /PID <PID> /F
  ```

## Environment Variables

### Backend (.env or docker-compose)
```
DATABASE_URL=postgresql+asyncpg://ainews:ainews_secret@localhost:5432/ainews
REDIS_URL=redis://localhost:6379/0
MODEL_NAME=distilbert-base-uncased
MINIO_ENDPOINT=localhost:9000
HF_MODEL_REPO=  # Optional: HuggingFace model repo for Model A (e.g., username/model-name)
AB_MODEL_B_HF_REPO=  # Optional: HuggingFace model repo for Model B in A/B testing
HF_TOKEN=       # Optional: HuggingFace API token
```

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Performance Expectations

| Operation | Time | Notes |
|-----------|------|-------|
| Prediction (cached) | <100ms | With caching enabled, no explanation |
| Prediction (fresh) | 1-2s | First prediction of text |
| Prediction + Explanation | 5-10s | Expensive attention computation |
| Model Load (first time) | 30-60s | HuggingFace download + load |
| Model Load (cached) | 2-5s | From disk |

## Debugging

### Enable Verbose Logging
Backend:
```python
# In app/main.py or services, add:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Database
```bash
# Connect to PostgreSQL
psql postgresql://ainews:ainews_secret@localhost:5432/ainews

# View predictions table
SELECT id, predicted_name, confidence, created_at FROM prediction_logs ORDER BY created_at DESC LIMIT 10;
```

### Monitor Performance
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001
- MLFlow: http://localhost:5000

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f <service>`
2. Review TECHNICAL_ANALYSIS.md for detailed fix information
3. Review PREDICT_ROUTE_FIX.md for testing procedures
