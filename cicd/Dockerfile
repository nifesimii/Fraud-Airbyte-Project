
FROM apache/airflow:3.0.2-python3.11

USER airflow

# Only install your custom Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# DON'T copy DAGs - they come from git-sync now