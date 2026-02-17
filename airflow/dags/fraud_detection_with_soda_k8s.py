"""
Fraud Detection Pipeline with Soda Data Quality Checks (KubernetesPodOperator)

- Airbyte Cloud syncs triggered via REST API (no airbyte provider needed)
- Fresh Airbyte access token fetched at runtime via client_credentials grant
- Soda checks run in isolated K8s pods with config mounted from ConfigMap
- dbt transforms run via Cosmos (astronomer-cosmos) after quality checks pass
- Soda files: soda/configuration.yml, soda/checks/*.yml
- ConfigMap: k8s/soda-configmap.yaml

Credentials are loaded from environment variables (via K8s Secret "airbyte-secrets").
"""

import os
import requests
from datetime import datetime, timedelta
import time

from airflow.sdk import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client import models as k8s
from cosmos import DbtTaskGroup, ProjectConfig, ProfileConfig, RenderConfig
from cosmos.profiles import SnowflakeUserPasswordProfileMapping


# ===================================================================
# Load credentials from environment variables
# ===================================================================
SNOWFLAKE_ACCOUNT = os.environ["SNOWFLAKE_ACCOUNT"]
SNOWFLAKE_USER = os.environ["SNOWFLAKE_USER"]
SNOWFLAKE_PASSWORD = os.environ["SNOWFLAKE_PASSWORD"]
SNOWFLAKE_DATABASE = os.environ["SNOWFLAKE_DATABASE"]
SNOWFLAKE_WAREHOUSE = os.environ["SNOWFLAKE_WAREHOUSE"]
SNOWFLAKE_ROLE = os.environ["SNOWFLAKE_ROLE"]

AIRBYTE_CLIENT_ID = os.environ["AIRBYTE_CLIENT_ID"]
AIRBYTE_CLIENT_SECRET = os.environ["AIRBYTE_CLIENT_SECRET"]
AIRBYTE_CONN_ID = os.environ.get(
    "AIRBYTE_CONNECTION_ID",
    os.environ.get("AIRBYTE_CONN_S3_SNOWFLAKE", ""),
)

AIRBYTE_API_BASE = "https://api.airbyte.com"


# ===================================================================
# Helper: fetch a fresh Airbyte access token using client credentials
# ===================================================================
def fetch_airbyte_token(**context):
    """
    Exchange client_id + client_secret for a short-lived access token.
    Pushes the token to XCom so downstream tasks can use it.
    """
    response = requests.post(
        f"{AIRBYTE_API_BASE}/v1/applications/token",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        json={
            "client_id": AIRBYTE_CLIENT_ID,
            "client_secret": AIRBYTE_CLIENT_SECRET,
            "grant-type": "client_credentials",
        },
    )
    response.raise_for_status()
    token = response.json()["access_token"]
    context["ti"].xcom_push(key="airbyte_token", value=token)
    return token


# ===================================================================
# Helper: trigger Airbyte sync using the fresh token
# ===================================================================
def trigger_sync(**context):
    """Trigger an Airbyte Cloud sync job and return the job ID."""
    token = context["ti"].xcom_pull(task_ids="get_airbyte_token", key="airbyte_token")
    response = requests.post(
        f"{AIRBYTE_API_BASE}/v1/jobs",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        json={
            "connectionId": AIRBYTE_CONN_ID,
            "jobType": "sync",
        },
    )
    response.raise_for_status()
    job_id = response.json()["jobId"]
    context["ti"].xcom_push(key="airbyte_job_id", value=str(job_id))
    return job_id


# ===================================================================
# Helper: poll Airbyte job until completion
# ===================================================================
def wait_for_sync_completion(**context):
    """Poll Airbyte job status until succeeded or failed."""
    token = context["ti"].xcom_pull(task_ids="get_airbyte_token", key="airbyte_token")
    job_id = context["ti"].xcom_pull(task_ids="trigger_airbyte_sync", key="airbyte_job_id")

    timeout = 3600  # 1 hour
    poke_interval = 30
    elapsed = 0

    while elapsed < timeout:
        response = requests.get(
            f"{AIRBYTE_API_BASE}/v1/jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        status = response.json()["status"]
        print(f"Airbyte job {job_id} status: {status}")

        if status == "succeeded":
            return status
        elif status == "failed":
            raise Exception(f"Airbyte sync job {job_id} failed!")

        time.sleep(poke_interval)
        elapsed += poke_interval

    raise TimeoutError(f"Airbyte sync job {job_id} timed out after {timeout}s")


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
    image="soda-core-arm:latest",
    image_pull_policy="IfNotPresent",
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
    description="Fraud detection pipeline with Soda quality checks and dbt transforms",
    schedule=timedelta(hours=6),
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["fraud", "soda", "dbt", "data-quality", "kubernetes"],
) as dag:

    # -----------------------------------------------------------------
    # STEP 1: Get a fresh Airbyte access token
    # -----------------------------------------------------------------
    get_airbyte_token = PythonOperator(
        task_id="get_airbyte_token",
        python_callable=fetch_airbyte_token,
    )

    # -----------------------------------------------------------------
    # STEP 2: Trigger Airbyte Cloud sync
    # -----------------------------------------------------------------
    trigger_airbyte_sync = PythonOperator(
        task_id="trigger_airbyte_sync",
        python_callable=trigger_sync,
    )

    # -----------------------------------------------------------------
    # STEP 3: Wait for Airbyte sync to complete
    # -----------------------------------------------------------------
    wait_for_sync = PythonOperator(
        task_id="wait_for_sync",
        python_callable=wait_for_sync_completion,
    )

    # -----------------------------------------------------------------
    # STEP 4a: Soda quality checks — Transactions
    # -----------------------------------------------------------------
    soda_check_transactions = KubernetesPodOperator(
        task_id="soda_quality_check_transactions",
        name="soda-transactions-check",
        cmds=soda_scan_command("labeled_transactions_staging_checks.yml")[0:2],
        arguments=[soda_scan_command("labeled_transactions_staging_checks.yml")[2]],
        **SODA_POD_DEFAULTS,
    )

    # -----------------------------------------------------------------
    # STEP 4b: Soda quality checks — Customers
    # -----------------------------------------------------------------
    soda_check_customers = KubernetesPodOperator(
        task_id="soda_quality_check_customers",
        name="soda-customers-check",
        cmds=soda_scan_command("customer_staging_checks.yml")[0:2],
        arguments=[soda_scan_command("customer_staging_checks.yml")[2]],
        **SODA_POD_DEFAULTS,
    )

    # -----------------------------------------------------------------
    # STEP 5: dbt — Build customer metrics table in Snowflake
    # -----------------------------------------------------------------
    dbt_customer_metrics = DbtTaskGroup(
        group_id="dbt_customer_metrics",
        project_config=ProjectConfig(
            dbt_project_path="/opt/airflow/dags/repo/dbt/fraud_analytics",
        ),
        profile_config=ProfileConfig(
            profile_name="fraud_analytics",
            target_name="prod",
            profile_mapping=SnowflakeUserPasswordProfileMapping(
                conn_id="snowflake_default",
            ),
        ),
        render_config=RenderConfig(
            select=["path:models/marts/customer_metrics.sql"],
        ),
    )

    # -----------------------------------------------------------------
    # Pipeline dependencies
    # -----------------------------------------------------------------
    (
        get_airbyte_token
        >> trigger_airbyte_sync
        >> wait_for_sync
        >> [soda_check_transactions, soda_check_customers]
        >> dbt_customer_metrics
    )