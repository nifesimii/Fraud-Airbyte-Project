# Airbyte Cloud Integration

## Setup

### 1. Get API Key

1. Go to https://cloud.airbyte.com
2. Settings → Developer → API Keys
3. Create new key: "Airflow Integration"
4. Copy the key immediately

### 2. Add Connection in Airflow

In Airflow UI (http://localhost:8080):

**Admin** → **Connections** → **+**
```
Connection Id: airbyte_cloud
Connection Type: HTTP
Host: https://api.airbyte.com
Extra: {"Authorization": "Bearer YOUR_API_KEY"}
```

### 3. Create Source & Destination in Airbyte Cloud

1. Go to https://cloud.airbyte.com
2. **Sources** → Add source (e.g., PostgreSQL, API, etc.)
3. **Destinations** → Add destination (e.g., Snowflake, BigQuery)
4. **Connections** → Create connection
5. Copy the **Connection ID** (you'll need this in DAGs)

### 4. Example DAG
```python
from airflow import DAG
from airflow.providers.http.operators.http import SimpleHttpOperator
from datetime import datetime
import json

with DAG(
    'airbyte_sync',
    start_date=datetime(2026, 1, 1),
    schedule_interval='@daily',
    catchup=False
) as dag:
    
    trigger_sync = SimpleHttpOperator(
        task_id='trigger_airbyte',
        http_conn_id='airbyte_cloud',
        endpoint='/v1/jobs',
        method='POST',
        headers={'Content-Type': 'application/json'},
        data=json.dumps({
            'connectionId': 'YOUR_CONNECTION_ID',
            'jobType': 'sync'
        }),
        response_check=lambda r: r.status_code == 200
    )
```

## API Reference

- Docs: https://reference.airbyte.com/reference/start
- Trigger sync: `POST /v1/jobs`
- Check status: `GET /v1/jobs/{jobId}`
- List connections: `GET /v1/connections`

## Benefits

✅ No infrastructure management
✅ Auto-scaling
✅ 300+ pre-built connectors
✅ Built-in monitoring
✅ Free tier: 100GB/month
