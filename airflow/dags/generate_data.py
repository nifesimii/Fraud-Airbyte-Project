from airflow.decorators import dag, task
from datetime import datetime, timedelta
import random
import psycopg2
from psycopg2 import sql
import mysql.connector
from mysql.connector import Error


@dag(schedule='@daily', start_date=datetime(2024, 1, 1), catchup=False)
def generate_fraud_detection_data():
    """
    DAG to generate transaction data and fraud detection labels.
    All logic is contained within this single file.
    """
    
    @task
    def generate_transaction_data(logical_date=None):
        """
        Generate customer transactions and insert into PostgreSQL.
        """
        # Database connection parameters
        conn_params = {
            "host": "airbyte-db",
            "database": "airbyte",
            "user": "docker",
            "password": "docker"
        }
        
        def create_transactions_table():
            """Create the customer_transactions table if it doesn't exist."""
            create_table_query = """
            CREATE TABLE IF NOT EXISTS customer_transactions (
                transaction_id SERIAL PRIMARY KEY,
                user_id INT NOT NULL,
                transaction_date TIMESTAMP NOT NULL,
                amount DECIMAL(10, 2) NOT NULL
            );
            """
            conn = None
            try:
                conn = psycopg2.connect(**conn_params)
                cur = conn.cursor()
                cur.execute(create_table_query)
                conn.commit()
                cur.close()
                print("✓ Transactions table created/verified")
            except Exception as e:
                print(f"Error creating table: {e}")
                raise
            finally:
                if conn is not None:
                    conn.close()
        
        def generate_transactions(user_id, num_transactions, data_interval_start):
            """Generate transaction data for a given user."""
            transactions = []
            for _ in range(num_transactions):
                if data_interval_start is not None:
                    transaction_date = data_interval_start + timedelta(
                        hours=random.randint(0, 23), 
                        minutes=random.randint(0, 59)
                    )
                else:
                    transaction_date = datetime.now() - timedelta(
                        hours=random.randint(1, 23), 
                        minutes=random.randint(0, 59)
                    )
                amount = round(random.uniform(5.0, 500.0), 2)
                transactions.append((user_id, transaction_date, amount))
            return transactions
        
        def insert_transactions(transactions):
            """Insert transaction data into PostgreSQL."""
            query = sql.SQL(
                "INSERT INTO customer_transactions (user_id, transaction_date, amount) VALUES (%s, %s, %s)"
            )
            conn = None
            try:
                conn = psycopg2.connect(**conn_params)
                cur = conn.cursor()
                cur.executemany(query, transactions)
                conn.commit()
                cur.close()
                print(f"✓ Inserted {len(transactions)} transactions")
            except Exception as e:
                print(f"Error inserting transactions: {e}")
                raise
            finally:
                if conn is not None:
                    conn.close()
        
        # Main execution
        create_transactions_table()
        
        num_users = 10
        total_transactions = 0
        for user_id in range(1, num_users + 1):
            num_txns = random.randint(5, 20)
            transactions = generate_transactions(user_id, num_txns, logical_date)
            insert_transactions(transactions)
            total_transactions += num_txns
        
        print(f"✓ Transaction data generation complete: {total_transactions} transactions for {num_users} users")
        return total_transactions
    
    @task
    def generate_fraud_labels(logical_date=None, **context):
        """
        Fetch transaction IDs from PostgreSQL and generate fraud labels in MySQL.
        """
        # PostgreSQL connection parameters
        postgres_params = {
            "host": "airbyte-db",
            "database": "airbyte",
            "user": "docker",
            "password": "docker"
        }
        
        # MySQL connection parameters
        mysql_params = {
            "host": "mysql",
            "database": "data",
            "user": "docker",
            "password": "docker"
        }
        
        def fetch_transaction_ids(data_interval_start):
            """Fetch transaction IDs from PostgreSQL for today's transactions."""
            if data_interval_start is not None:
                today = data_interval_start.strftime('%Y-%m-%d')
            else:
                today = datetime.now().strftime('%Y-%m-%d')
            
            fetch_query = """
            SELECT transaction_id FROM customer_transactions
            WHERE transaction_date >= %s AND transaction_date < %s::date + interval '1 day'
            ORDER BY transaction_id;
            """
            
            conn = None
            try:
                conn = psycopg2.connect(**postgres_params)
                cur = conn.cursor()
                cur.execute(fetch_query, (today, today))
                transaction_ids = [row[0] for row in cur.fetchall()]
                cur.close()
                print(f"✓ Fetched {len(transaction_ids)} transaction IDs")
                return transaction_ids
            except Exception as e:
                print(f"Error fetching transaction IDs: {e}")
                raise
            finally:
                if conn is not None:
                    conn.close()
        
        def insert_fraud_labels(transaction_ids):
            """Insert labeled transaction data into MySQL."""
            create_table_query = """
            CREATE TABLE IF NOT EXISTS labeled_transactions (
                transaction_id INT PRIMARY KEY,
                is_fraudulent BOOLEAN NOT NULL
            );
            """
            insert_query = "INSERT INTO labeled_transactions (transaction_id, is_fraudulent) VALUES (%s, %s)"
            
            conn = None
            try:
                conn = mysql.connector.connect(**mysql_params)
                cur = conn.cursor()
                cur.execute(create_table_query)
                
                fraud_count = 0
                for transaction_id in transaction_ids:
                    is_fraudulent = random.choice([True, False])
                    if is_fraudulent:
                        fraud_count += 1
                    cur.execute(insert_query, (transaction_id, is_fraudulent))
                
                conn.commit()
                cur.close()
                print(f"✓ Labeled {len(transaction_ids)} transactions ({fraud_count} fraudulent)")
            except Error as e:
                print(f"Error inserting labeled transactions: {e}")
                raise
            finally:
                if conn is not None and conn.is_connected():
                    conn.close()
        
        # Main execution
        transaction_ids = fetch_transaction_ids(logical_date)
        
        if transaction_ids:
            insert_fraud_labels(transaction_ids)
            return len(transaction_ids)
        else:
            print("⚠ No transaction IDs fetched. Skipping fraud label generation.")
            return 0
    
    # Define task dependencies
    generate_transaction_data() >> generate_fraud_labels()


# Instantiate the DAG
generate_fraud_detection_data()