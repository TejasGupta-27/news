# Predict Route Fix Documentation

## Issues Fixed

### 1. Backend Blocking on Prediction & Explanation
**Problem**: Synchronous `predict()` and `explain_prediction()` calls in async function blocked the event loop
**Solution**: Wrapped both calls with `asyncio.to_thread()` to run in thread pool

**Files Modified**:
- `backend/app/routers/predict.py` - Lines 37-48

### 2. Type Mismatch in Response
**Problem**: `PredictResponse` schema had `prediction_id: UUID | None` but code returned `str(log.id)`
**Solution**: Changed schema to `prediction_id: str | None`

**Files Modified**:
- `backend/app/schemas/prediction.py` - Line 13

### 3. Explanation Generation Failures
**Problem**: Unhandled exceptions in `explain_prediction()` could crash the API
**Solution**: Added try-except block and null checks, returns `None` on error

**Files Modified**:
- `backend/app/services/explainer.py` - Complete function rewritten

### 4. Toggle Button Not Working Properly
**Problem**: Toggling explanation didn't prompt re-prediction with new setting
**Solution**: Added `handleToggleExplain()` that clears result when toggled

**Files Modified**:
- `frontend/src/app/predict/page.tsx` - Lines 48-53

### 5. Poor Error Handling in Frontend
**Problem**: Vague error messages and no handling for missing explanations
**Solution**: 
- Better error messages with console logging
- Check for explanation array before rendering
- Fallback message if explanation requested but not generated
- Improved API error handling

**Files Modified**:
- `frontend/src/lib/api.ts` - Complete rewrite with error handling
- `frontend/src/app/predict/page.tsx` - Complete rewrite

## Testing Instructions

### 1. Start the Backend
```bash
cd /home/abhay/Documents/news
docker-compose up backend postgres redis minio mlflow
```

### 2. Wait for services to be healthy
The backend should start with "Uvicorn running on http://0.0.0.0:8000"

### 3. Check Backend Health
```bash
curl http://localhost:8000/api/health
# Should return: {"status":"ok"}
```

### 4. Start the Frontend
```bash
cd frontend
npm install
npm run dev
```

### 5. Test Predictions (without explanations)
1. Navigate to http://localhost:3000
2. Go to "Classify Article"
3. Paste a news article (at least 10 characters)
4. Toggle OFF "Include explanations (slower)"
5. Click "Classify"
6. Should get prediction in ~1-2 seconds

### 6. Test Predictions (with explanations)
1. Paste the same article again (may be cached, so use a different one)
2. Toggle ON "Include explanations (slower)"
3. Click "Classify"
4. Should get prediction + explanation tokens in ~5-10 seconds

### 7. Test Toggle Functionality
1. Make a prediction without explanations
2. Toggle ON "Include explanations"
3. The previous result should disappear (form clears)
4. Make a new prediction - should show explanations

## Performance Improvements

- **No Event Loop Blocking**: Predictions and explanations run in thread pool
- **Graceful Degradation**: If explanation generation fails, returns base prediction
- **Better Caching**: Non-explanation predictions still cached
- **Improved UX**: Loading states and error messages more informative

## Files Modified

```
backend/
  ├── app/
  │   ├── routers/predict.py       (Added asyncio import, wrapped calls)
  │   ├── schemas/prediction.py    (Changed prediction_id to str)
  │   └── services/explainer.py    (Added error handling)
frontend/
  ├── src/
  │   ├── app/predict/page.tsx     (Complete rewrite - UX improvements)
  │   └── lib/api.ts                (Better error handling)
```

## Backward Compatibility

- ✅ API response schema remains compatible (only type changed from UUID to str)
- ✅ All existing functionality preserved
- ✅ Caching still works
- ✅ Database operations unchanged

## Monitoring

Check logs for:
- "Error generating explanation:" - Indicates explanation generation failed (non-critical)
- "Model or tokenizer not loaded" - Indicates model loading issue (critical)
- Backend should show request processing time in logs
