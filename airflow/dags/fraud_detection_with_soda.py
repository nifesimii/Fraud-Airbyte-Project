from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
from soda.scan import Scan
import logging

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def run_soda_scan(data_source, checks_file):
    """Run Soda scan and return results"""
    scan = Scan()
    
    # Set Soda configuration
    scan.set_data_source_name(data_source)
    
    # Add configuration file
    scan.add_configuration_yaml_file('/opt/airflow/dags/repo/airflow/soda/configuration/configuration.yml')
    
    # Add checks file
    scan.add_sodacl_yaml_file(f'/opt/airflow/dags/repo/airflow/soda/checks/{checks_file}')
    
    # Execute scan
    scan.execute()
    
    # Log results
    logging.info(f"Scan results: {scan.get_logs_text()}")
    
    # Check if scan passed
    if scan.has_check_fails():
        raise ValueError(f"Soda scan failed! Check results: {scan.get_scan_results()}")
    
    return scan.get_scan_results()

def validate_source_data():
    """Validate source MySQL data"""
    logging.info("Running Soda checks on MySQL source...")
    results = run_soda_scan('mysql_source', 'transactions_checks.yml')
    logging.info(f"Source validation passed: {results}")
    return results

def validate_target_data():
    """Validate target PostgreSQL data"""
    logging.info("Running Soda checks on PostgreSQL target...")
    results = run_soda_scan('postgres_target', 'transactions_checks.yml')
    logging.info(f"Target validation passed: {results}")
    return results

def validate_users_data():
    """Validate users data"""
    logging.info("Running Soda checks on users table...")
    results = run_soda_scan('mysql_source', 'users_checks.yml')
    logging.info(f"Users validation passed: {results}")
    return results

with DAG(
    'fraud_detection_with_soda',
    default_args=default_args,
    description='Fraud detection pipeline with Soda data quality checks',
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['fraud', 'soda', 'data-quality'],
) as dag:
    
    # Step 1: Validate source data BEFORE processing
    validate_source = PythonOperator(
        task_id='validate_source_data',
        python_callable=validate_source_data,
    )
    
    # Step 2: Validate users data
    validate_users = PythonOperator(
        task_id='validate_users_data',
        python_callable=validate_users_data,
    )
    
    # Step 3: Generate fake transaction data
    generate_data = BashOperator(
        task_id='generate_transaction_data',
        bash_command='python /opt/airflow/dags/repo/airflow/dags/generate_data.py',
    )
    
    # Step 4: Manual Airbyte sync placeholder
    manual_sync_note = BashOperator(
        task_id='trigger_airbyte_sync',
        bash_command='echo "Run Airbyte sync manually from UI: http://cloud.airbyte.com"',
    )
    
    # Step 5: Validate target data AFTER sync
    validate_target = PythonOperator(
        task_id='validate_target_data',
        python_callable=validate_target_data,
    )
    
    # Step 6: Data quality report
    quality_report = BashOperator(
        task_id='generate_quality_report',
        bash_command='echo "All Soda checks passed! Data quality validated ✅"',
    )
    
    # Define task dependencies
    [validate_source, validate_users] >> generate_data >> manual_sync_note >> validate_target >> quality_report
