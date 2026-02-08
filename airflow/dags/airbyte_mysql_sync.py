from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.airbyte.operators.airbyte import AirbyteTriggerSyncOperator
from airflow.providers.airbyte.sensors.airbyte import AirbyteJobSensor

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'airbyte_mysql_fraud_sync',
    default_args=default_args,
    description='Sync fraud data from MySQL to Snowflake via Airbyte',
    schedule_interval='@hourly',
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=['airbyte', 'mysql', 'fraud'],
) as dag:

    trigger_sync = AirbyteTriggerSyncOperator(
        task_id='trigger_airbyte_sync',
        airbyte_conn_id='airbyte_cloud',
        connection_id='{{ var.value.airbyte_connection_id }}',
        asynchronous=True,
    )

    wait_for_sync = AirbyteJobSensor(
        task_id='wait_for_sync_completion',
        airbyte_conn_id='airbyte_cloud',
        airbyte_job_id=trigger_sync.output,
        timeout=3600,
        poke_interval=60,
    )

    trigger_sync >> wait_for_sync