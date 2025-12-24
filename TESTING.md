# Testing Guide for Query-Based Chat Execution

## Prerequisites

1. **Backend running** on `http://localhost:8000`
2. **Frontend running** on `http://localhost:3000`
3. **Environment variables** set (GROQ_API_KEY in `backend/.env`)

## Quick Start

### 1. Start Backend

```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### 2. Start Frontend

```bash
npm run dev
```

You should see:
```
✓ Ready in X ms
○ Local: http://localhost:3000
```

### 3. Test Dataset Upload

1. Go to `http://localhost:3000`
2. Upload a CSV or XLSX file (e.g., a dataset with columns like date, category, value)
3. Wait for profiling to complete

## Testing Query Execution

### Test Cases

#### ✅ Basic Questions

1. **"How many records are in this dataset?"**
   - Expected: Returns total row count
   - SQL: `SELECT COUNT(*) as count FROM data;`

2. **"What is the average of [numeric_column]?"**
   - Expected: Returns average value
   - SQL: `SELECT AVG(numeric_column) as average FROM data;`

3. **"Show me the first 10 rows"**
   - Expected: Returns table with first 10 rows
   - SQL: `SELECT * FROM data LIMIT 10;`

#### ✅ Time-Based Questions

4. **"Which year has the most records?"**
   - Expected: Returns year with highest count
   - SQL: `SELECT EXTRACT(YEAR FROM date_column) as year, COUNT(*) as count FROM data GROUP BY year ORDER BY count DESC LIMIT 1;`

5. **"Show records by month"**
   - Expected: Returns time series grouped by month
   - SQL: `SELECT EXTRACT(MONTH FROM date_column) as month, COUNT(*) as count FROM data GROUP BY month ORDER BY month;`

#### ✅ Category-Based Questions

6. **"Which category appears most frequently?"**
   - Expected: Returns category with highest count
   - SQL: `SELECT category_column, COUNT(*) as count FROM data GROUP BY category_column ORDER BY count DESC LIMIT 1;`

7. **"Show top 5 categories by count"**
   - Expected: Returns ranking of top 5 categories
   - SQL: `SELECT category_column, COUNT(*) as count FROM data GROUP BY category_column ORDER BY count DESC LIMIT 5;`

#### ✅ Aggregation Questions

8. **"What is the total of [numeric_column]?"**
   - Expected: Returns sum
   - SQL: `SELECT SUM(numeric_column) as total FROM data;`

9. **"What is the minimum value of [numeric_column]?"**
   - Expected: Returns minimum
   - SQL: `SELECT MIN(numeric_column) as minimum FROM data;`

#### ✅ Edge Cases

10. **"Show me everything"**
    - Expected: Should warn about large result or apply LIMIT
    - SQL: Should include `LIMIT 1000` or similar

11. **"Delete all records"**
    - Expected: Should return clarification (DELETE not allowed)
    - Result: `{"type": "clarification", "message": "..."}`

12. **"What is the meaning of life?"**
    - Expected: Should return clarification (not answerable with data)
    - Result: `{"type": "clarification", "message": "..."}`

## Checking Logs

### Backend Logs

Watch the backend terminal for:
- Query generation logs
- Validation warnings
- Execution times
- Errors

Example log output:
```
INFO - Processing question for dataset abc123: How many records?
INFO - Generated query type: sql, confidence: 0.9
INFO - Query executed successfully: 1 rows, 45.23ms
```

### Frontend Console

Open browser DevTools (F12) and check:
- Network tab for API calls
- Console for any errors
- Response payloads

## Manual API Testing

### Using curl

```bash
# Test query execution
curl -X POST "http://localhost:8000/api/chat/{dataset_id}/execute" \
  -H "Content-Type: application/json" \
  -d '{"question": "How many records are in this dataset?"}'
```

### Using Python

```python
import requests

response = requests.post(
    "http://localhost:8000/api/chat/{dataset_id}/execute",
    json={"question": "How many records are in this dataset?"}
)
print(response.json())
```

## Verification Checklist

- [ ] Backend starts without errors
- [ ] Frontend connects to backend
- [ ] Dataset uploads successfully
- [ ] Basic count questions work
- [ ] Aggregation questions work
- [ ] Time-based questions work
- [ ] Category questions work
- [ ] Invalid queries are rejected
- [ ] Clarification requests work
- [ ] Results are formatted correctly
- [ ] No raw data sent to LLM (check logs)
- [ ] Execution times are reasonable (< 2s)

## Common Issues

### Issue: "Groq client not initialized"
**Solution**: Set `GROQ_API_KEY` in `backend/.env`

### Issue: "Query validation failed"
**Solution**: Check that query only uses SELECT statements and valid columns

### Issue: "Query execution failed"
**Solution**: Check column names match schema, verify data types

### Issue: "Timeout"
**Solution**: Query may be too complex, try simpler question

## Performance Testing

Test with different dataset sizes:
- Small (< 1K rows)
- Medium (1K - 100K rows)
- Large (> 100K rows)

Monitor:
- Query generation time
- Execution time
- Memory usage
- Response size

