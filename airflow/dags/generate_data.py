from airflow.decorators import dag, task
from datetime import datetime
from includes.scripts.transaction_generator import main as _generate_transaction_data
from includes.scripts.detection_generator import main as _generate_fraud_data


@dag(schedule='@daily', start_date=datetime(2024, 1, 1), catchup=False)
def generate_data():
    @task
    def generate_transaction_data(logical_date=None):
        _generate_transaction_data(logical_date)

    @task
    def generate_fraud_data(logical_date=None):
        _generate_fraud_data(logical_date)

    # Airflow 3.0 way: Use bit-shift operator or @task.chain()
    generate_transaction_data() >> generate_fraud_data()


generate_data()