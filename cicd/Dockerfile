# FROM apache/airflow:3.0.2-python3.11

# # Copy DAGs to the container
# COPY dags/ /opt/airflow/dags/

# # Copy requirements file
# COPY requirements.txt .

# # Install additional Python packages
# RUN pip install --no-cache-dir -r requirements.txt


FROM docker.io/apache/airflow:3.0.2-python3.11

COPY dags/ /opt/airflow/dags/

# Copy from current context (airflow directory)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt