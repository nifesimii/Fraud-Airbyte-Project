FROM apache/airflow:3.0.2-python3.11
USER airflow

# Copy DAGs
COPY dags/ /opt/airflow/dags/

# Copy requirements
COPY ./requirements.txt .

# Install dependencies with DOUBLE DASH
RUN pip install --no-cache-dir -r requirements.txt