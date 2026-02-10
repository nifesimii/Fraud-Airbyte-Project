"""
Fraud Detection Pipeline with Data Quality Checks
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.airbyte.operators.airbyte import AirbyteTriggerSyncOperator
from airflow.providers.airbyte.sensors.airbyte import AirbyteJobSensor
import os

default_args = {
    'owner': 'data_team',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def set_soda_env_vars(**context):
    """Set Snowflake credentials from Airflow connection"""
    from airflow.hooks.base import BaseHook
    
    conn = BaseHook.get_connection('snowflake_default')
    extra = conn.extra_dejson
    
    os.environ['SNOWFLAKE_ACCOUNT'] = extra.get('account')
    os.environ['SNOWFLAKE_USER'] = conn.login
    os.environ['SNOWFLAKE_PASSWORD'] = conn.password
    os.environ['SNOWFLAKE_DATABASE'] = extra.get('database')
    os.environ['SNOWFLAKE_WAREHOUSE'] = extra.get('warehouse')
    os.environ['SNOWFLAKE_ROLE'] = extra.get('role', 'SYSADMIN')

with DAG(
    'fraud_detection_with_quality_checks',
    default_args=default_args,
    description='Fraud detection pipeline with Soda quality checks',
    schedule_interval='0 */6 * * *',  # Every 6 hours
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['fraud', 'data-quality', 'soda'],
) as dag:

    # Step 1: Sync data from MySQL to Snowflake via Airbyte
    sync_transactions = AirbyteTriggerSyncOperator(
        task_id='sync_transactions_to_snowflake',
        airbyte_conn_id='airbyte_cloud',
        connection_id='YOUR_AIRBYTE_CONNECTION_ID',  # Replace with actual ID
        asynchronous=True,
    )

    wait_for_sync = AirbyteJobSensor(
        task_id='wait_for_transactions_sync',
        airbyte_conn_id='airbyte_cloud',
        airbyte_job_id="{{ task_instance.xcom_pull(task_ids='sync_transactions_to_snowflake', key='job_id') }}",
    )

    # Step 2: Set Snowflake credentials for Soda
    set_env = PythonOperator(
        task_id='set_snowflake_credentials',
        python_callable=set_soda_env_vars,
    )

    # Step 3: Run Soda quality checks on staging data
    soda_scan_transactions = BashOperator(
        task_id='quality_check_transactions',
        bash_command="""
        cd /opt/airflow/dags/repo/soda
        soda scan \
          -d snowflake_staging \
          -c configuration/configuration.yml \
          checks/transactions_staging.yml
        """,
        env={
            'SNOWFLAKE_ACCOUNT': '{{ var.value.SNOWFLAKE_ACCOUNT }}',
            'SNOWFLAKE_USER': '{{ var.value.SNOWFLAKE_USER }}',
            'SNOWFLAKE_PASSWORD': '{{ var.value.SNOWFLAKE_PASSWORD }}',
            'SNOWFLAKE_DATABASE': '{{ var.value.SNOWFLAKE_DATABASE }}',
            'SNOWFLAKE_WAREHOUSE': '{{ var.value.SNOWFLAKE_WAREHOUSE }}',
            'SNOWFLAKE_ROLE': '{{ var.value.SNOWFLAKE_ROLE }}',
        }
    )

    soda_scan_customers = BashOperator(
        task_id='quality_check_customers',
        bash_command="""
        cd /opt/airflow/dags/repo/soda
        soda scan \
          -d snowflake_staging \
          -c configuration/configuration.yml \
          checks/customers_staging.yml
        """,
        env={
            'SNOWFLAKE_ACCOUNT': '{{ var.value.SNOWFLAKE_ACCOUNT }}',
            'SNOWFLAKE_USER': '{{ var.value.SNOWFLAKE_USER }}',
            'SNOWFLAKE_PASSWORD': '{{ var.value.SNOWFLAKE_PASSWORD }}',
            'SNOWFLAKE_DATABASE': '{{ var.value.SNOWFLAKE_DATABASE }}',
            'SNOWFLAKE_WAREHOUSE': '{{ var.value.SNOWFLAKE_WAREHOUSE }}',
            'SNOWFLAKE_ROLE': '{{ var.value.SNOWFLAKE_ROLE }}',
        }
    )

    # Step 4: Placeholder for dbt transformation (add later)
    # This would run after quality checks pass
    run_dbt_models = BashOperator(
        task_id='transform_with_dbt',
        bash_command='echo "dbt run --models fraud_detection"',
    )

    # Define task dependencies
    sync_transactions >> wait_for_sync >> set_env
    set_env >> [soda_scan_transactions, soda_scan_customers]
    [soda_scan_transactions, soda_scan_customers] >> run_dbt_models

