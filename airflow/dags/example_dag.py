"""
Example Airflow DAG demonstrating basic operators.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

# Default arguments
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Python function for PythonOperator
def print_hello():
    print("Hello from Airflow!")
    return "Hello World!"

# Define the DAG
with DAG(
    'example_dag',
    default_args=default_args,
    description='A simple example DAG',
    schedule=timedelta(days=1),  # Changed from schedule_interval to schedule
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['example'],
) as dag:
    # Task 1: Bash command
    task_1 = BashOperator(
        task_id='print_date',
        bash_command='date',
    )
    
    # Task 2: Python function
    task_2 = PythonOperator(
        task_id='print_hello',
        python_callable=print_hello,
    )
    
    # Task 3: Another bash command
    task_3 = BashOperator(
        task_id='sleep',
        bash_command='sleep 5',
    )
    
    # Define task dependencies
    task_1 >> task_2 >> task_3