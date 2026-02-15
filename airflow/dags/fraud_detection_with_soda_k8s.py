"""
Fraud Detection Pipeline with Soda Data Quality Checks (KubernetesPodOperator)

- Airbyte Cloud syncs triggered via REST API (no airbyte provider needed)
- Soda checks run in isolated K8s pods with config mounted from ConfigMap
- Soda files: soda/configuration.yml, soda/checks/*.yml
- ConfigMap: k8s/soda-configmap.yaml

Credentials are loaded from environment variables.
Set them in your Airflow deployment via:
  - A .env file loaded by docker-compose (env_file directive)
  - Or export them in the Airflow worker/scheduler environment
  - Or set them in your Helm values (extraEnv / extraEnvFrom)
"""

import os
from datetime import datetime, timedelta
import json

from airflow.sdk import DAG
from airflow.providers.http.operators.http import HttpOperator
from airflow.providers.http.sensors.http import HttpSensor
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client import models as k8s


# ===================================================================
# Load credentials from environment variables
# ===================================================================
SNOWFLAKE_ACCOUNT = os.environ["SNOWFLAKE_ACCOUNT"]
SNOWFLAKE_USER = os.environ["SNOWFLAKE_USER"]
SNOWFLAKE_PASSWORD = os.environ["SNOWFLAKE_PASSWORD"]
SNOWFLAKE_DATABASE = os.environ["SNOWFLAKE_DATABASE"]
SNOWFLAKE_WAREHOUSE = os.environ["SNOWFLAKE_WAREHOUSE"]
SNOWFLAKE_ROLE = os.environ["SNOWFLAKE_ROLE"]

AIRBYTE_ACCESS_TOKEN = os.environ["AIRBYTE_ACCESS_TOKEN"]
AIRBYTE_CONN_ID = os.environ.get(
    "AIRBYTE_CONNECTION_ID",
    os.environ.get("AIRBYTE_CONN_S3_SNOWFLAKE", ""),
)


# ===================================================================
# Shared K8s volume config for mounting Soda ConfigMap
# ===================================================================
soda_volume = k8s.V1Volume(
    name="soda-config",
    config_map=k8s.V1ConfigMapVolumeSource(name="soda-config"),
)

soda_volume_mount = k8s.V1VolumeMount(
    name="soda-config",
    mount_path="/soda",
    read_only=True,
)

# These env vars are passed into the Soda K8s pods so soda can connect to Snowflake
SNOWFLAKE_ENV_VARS = {
    "SNOWFLAKE_ACCOUNT": SNOWFLAKE_ACCOUNT,
    "SNOWFLAKE_USER": SNOWFLAKE_USER,
    "SNOWFLAKE_PASSWORD": SNOWFLAKE_PASSWORD,
    "SNOWFLAKE_DATABASE": SNOWFLAKE_DATABASE,
    "SNOWFLAKE_WAREHOUSE": SNOWFLAKE_WAREHOUSE,
    "SNOWFLAKE_ROLE": SNOWFLAKE_ROLE,
}

SODA_POD_DEFAULTS = dict(
    namespace="airflow",
    image="sodadata/soda-core:latest",
    get_logs=True,
    log_events_on_failure=True,
    is_delete_operator_pod=True,
    in_cluster=True,
    service_account_name="airflow-worker",
    volumes=[soda_volume],
    volume_mounts=[soda_volume_mount],
    env_vars=SNOWFLAKE_ENV_VARS,
)


def soda_scan_command(checks_file: str) -> list[str]:
    """Generate the shell command to run a Soda scan against a specific checks file."""
    return [
        "sh",
        "-c",
        f"""
        set -e
        echo "Running Soda scan with /soda/{checks_file}..."
        soda scan -d staging -c /soda/configuration.yml /soda/{checks_file}
        echo "Soda scan complete."
        """,
    ]


# ===================================================================
# DAG Definition
# ===================================================================
default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="fraud_detection_with_soda_k8s",
    default_args=default_args,
    description="Fraud detection pipeline with Soda quality checks via K8s pods",
    schedule=timedelta(hours=6),
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["fraud", "soda", "data-quality", "kubernetes"],
) as dag:

    # -----------------------------------------------------------------
    # STEP 1: Trigger Airbyte Cloud sync via REST API
    # -----------------------------------------------------------------
    # Uses the Airbyte access token directly from env vars.
    # No Airflow HTTP connection needed — headers are set inline.
    # -----------------------------------------------------------------
    trigger_airbyte_sync = HttpOperator(
        task_id="trigger_airbyte_sync",
        http_conn_id="airbyte_cloud",
        endpoint="/v1/jobs",
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AIRBYTE_ACCESS_TOKEN}",
        },
        data=json.dumps({
            "connectionId": AIRBYTE_CONN_ID,
            "jobType": "sync",
        }),
        response_filter=lambda response: response.json()["jobId"],
        log_response=True,
    )

    # -----------------------------------------------------------------
    # STEP 2: Wait for Airbyte Cloud sync to complete
    # -----------------------------------------------------------------
    wait_for_sync = HttpSensor(
        task_id="wait_for_sync",
        http_conn_id="airbyte_cloud",
        endpoint="/v1/jobs/{{ task_instance.xcom_pull(task_ids='trigger_airbyte_sync') }}",
        method="GET",
        headers={
            "Authorization": f"Bearer {AIRBYTE_ACCESS_TOKEN}",
        },
        response_check=lambda response: response.json()["status"] in [
            "succeeded",
            "failed",
        ],
        poke_interval=30,
        timeout=3600,
    )

    # -----------------------------------------------------------------
    # STEP 3a: Soda quality checks — Transactions
    # -----------------------------------------------------------------
    soda_check_transactions = KubernetesPodOperator(
        task_id="soda_quality_check_transactions",
        name="soda-transactions-check",
        cmds=soda_scan_command("transactions_checks.yml")[0:2],
        arguments=[soda_scan_command("transactions_checks.yml")[2]],
        **SODA_POD_DEFAULTS,
    )

    # -----------------------------------------------------------------
    # STEP 3b: Soda quality checks — Customers
    # -----------------------------------------------------------------
    soda_check_customers = KubernetesPodOperator(
        task_id="soda_quality_check_customers",
        name="soda-customers-check",
        cmds=soda_scan_command("customers_checks.yml")[0:2],
        arguments=[soda_scan_command("customers_checks.yml")[2]],
        **SODA_POD_DEFAULTS,
    )

    # -----------------------------------------------------------------
    # STEP 4: Pipeline dependencies
    # -----------------------------------------------------------------
    trigger_airbyte_sync >> wait_for_sync >> [
        soda_check_transactions,
        soda_check_customers,
    ]