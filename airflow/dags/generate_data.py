from airflow.decorators import dag, task
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.mysql.hooks.mysql import MySqlHook
from datetime import datetime, timedelta
import random


@dag(
    schedule='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['fraud-detection', 'data-generation'],
    doc_md="""
    ## Fraud Detection Data Generation Pipeline
    
    This DAG generates fraud detection data:
    1. Generates transaction data in PostgreSQL source
    2. Generates fraud labels in MySQL source
    
    ### Databases:
    - **PostgreSQL Source**: fraud_analytics.customer_transactions
    - **MySQL Source**: fraud_data.labeled_transactions
    
    ### Next Steps:
    After this DAG completes, manually trigger Airbyte Cloud syncs to move
    data to your destination (Snowflake/BigQuery/S3).
    """
)
def fraud_detection_pipeline():
    """
    End-to-end fraud detection data pipeline using Airbyte Cloud.
    """
    
    @task
    def generate_transaction_data(logical_date=None):
        """
        Generate customer transactions and insert into PostgreSQL source database.
        Database: postgres_source (fraud_analytics)
        """
        postgres_hook = PostgresHook(postgres_conn_id='postgres_source')
        
        def create_transactions_table():
            """Create the customer_transactions table if it doesn't exist."""
            create_table_query = """
            CREATE TABLE IF NOT EXISTS customer_transactions (
                transaction_id SERIAL NOT NULL,
                customer_id INTEGER NOT NULL,
                transaction_date TIMESTAMP NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                merchant VARCHAR(255),
                location VARCHAR(255),
                transaction_type VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (customer_id, transaction_id)
            );
            
            -- Create index for better query performance
            CREATE INDEX IF NOT EXISTS idx_transaction_date 
            ON customer_transactions(transaction_date);
            """
            
            try:
                postgres_hook.run(create_table_query)
                print("✅ Transactions table created/verified")
            except Exception as e:
                print(f"❌ Error creating table: {e}")
                raise
        
        def generate_transactions(customer_id, num_transactions, data_interval_start):
            """Generate realistic transaction data for a given customer."""
            merchants = [
                'Amazon', 'Walmart', 'Target', 'Shoprite', 'Jumia',
                'Netflix', 'Spotify', 'Apple Store', 'Gas Station', 'Restaurant'
            ]
            locations = [
                'Lagos, Nigeria', 'Accra, Ghana', 'Nairobi, Kenya',
                'New York, USA', 'London, UK', 'Online'
            ]
            transaction_types = ['purchase', 'refund', 'subscription', 'transfer']
            
            transactions = []
            for _ in range(num_transactions):
                if data_interval_start is not None:
                    transaction_date = data_interval_start + timedelta(
                        hours=random.randint(0, 23),
                        minutes=random.randint(0, 59),
                        seconds=random.randint(0, 59)
                    )
                else:
                    transaction_date = datetime.now() - timedelta(
                        hours=random.randint(1, 23),
                        minutes=random.randint(0, 59)
                    )
                
                txn_type = random.choice(transaction_types)
                if txn_type == 'subscription':
                    amount = round(random.uniform(5.0, 50.0), 2)
                elif txn_type == 'refund':
                    amount = -round(random.uniform(10.0, 500.0), 2)
                else:
                    amount = round(random.uniform(5.0, 5000.0), 2)
                
                transactions.append((
                    customer_id,
                    transaction_date,
                    amount,
                    random.choice(merchants),
                    random.choice(locations),
                    txn_type
                ))
            return transactions
        
        def insert_transactions(transactions):
            """Insert transaction data into PostgreSQL."""
            try:
                conn = postgres_hook.get_conn()
                cursor = conn.cursor()
                insert_query = """
                INSERT INTO customer_transactions 
                (customer_id, transaction_date, amount, merchant, location, transaction_type)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.executemany(insert_query, transactions)
                conn.commit()
                cursor.close()
                conn.close()
                print(f"✅ Inserted {len(transactions)} transactions")
            except Exception as e:
                print(f"❌ Error inserting transactions: {e}")
                raise
        
        # Main execution
        create_transactions_table()
        
        num_customers = 20
        total_transactions = 0
        
        for customer_num in range(1, num_customers + 1):
            customer_id = customer_num  # strictly an integer
            num_txns = random.randint(5, 30)
            transactions = generate_transactions(customer_id, num_txns, logical_date)
            insert_transactions(transactions)
            total_transactions += num_txns
        
        print(f"✅ Generated {total_transactions} transactions for {num_customers} customers")
        return {'total_transactions': total_transactions, 'num_customers': num_customers}
    
    @task
    def generate_fraud_labels(logical_date=None, **context):
        """
        Fetch transaction IDs from PostgreSQL and generate fraud labels in MySQL.
        Reads from: postgres_source.fraud_analytics.customer_transactions
        Writes to: mysql_default.fraud_data.labeled_transactions
        """
        postgres_hook = PostgresHook(postgres_conn_id='postgres_source')
        mysql_hook = MySqlHook(mysql_conn_id='mysql_default')
        
        def fetch_transaction_ids(data_interval_start):
            """Fetch transaction IDs from PostgreSQL for today's transactions."""
            if data_interval_start is not None:
                today = data_interval_start.strftime('%Y-%m-%d')
            else:
                today = datetime.now().strftime('%Y-%m-%d')
            
            fetch_query = """
            SELECT transaction_id, amount, merchant, location
            FROM customer_transactions
            WHERE DATE(transaction_date) = %s
            ORDER BY transaction_id;
            """
            
            try:
                conn = postgres_hook.get_conn()
                cursor = conn.cursor()
                cursor.execute(fetch_query, (today,))
                transactions = cursor.fetchall()
                cursor.close()
                conn.close()
                print(f"✅ Fetched {len(transactions)} transaction IDs from PostgreSQL")
                return transactions
            except Exception as e:
                print(f"❌ Error fetching transaction IDs: {e}")
                raise
        
        def insert_fraud_labels(transactions):
            """
            Insert labeled transaction data into MySQL with fraud detection logic.
            Uses heuristics to determine fraud probability.
            """
            create_table_query = """
            CREATE TABLE IF NOT EXISTS labeled_transactions (
                transaction_id INT PRIMARY KEY,
                is_fraudulent BOOLEAN NOT NULL,
                fraud_score DECIMAL(5, 2),
                fraud_reason VARCHAR(255),
                labeled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_fraud_flag (is_fraudulent),
                INDEX idx_labeled_at (labeled_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            
            try:
                mysql_hook.run(create_table_query)
                print("✅ MySQL fraud labels table created/verified")
                
                fraud_count = 0
                labels = []
                
                for transaction in transactions:
                    transaction_id, amount, merchant, location = transaction
                    
                    fraud_score = 0.0
                    fraud_reasons = []
                    
                    if amount > 3000:
                        fraud_score += 30
                        fraud_reasons.append('High amount')
                    
                    if 'Online' in location:
                        fraud_score += 10
                        fraud_reasons.append('Online transaction')
                    
                    random_score = random.uniform(0, 40)
                    fraud_score += random_score
                    
                    is_fraudulent = fraud_score >= 50
                    if is_fraudulent:
                        fraud_count += 1
                    
                    fraud_reason = ', '.join(fraud_reasons) if fraud_reasons else 'Low risk'
                    
                    labels.append((
                        int(transaction_id),
                        is_fraudulent,
                        round(fraud_score, 2),
                        fraud_reason
                    ))
                
                # Use executemany instead of insert_rows (provider bug workaround)
                conn = mysql_hook.get_conn()
                cursor = conn.cursor()
                insert_query = """
                INSERT INTO labeled_transactions 
                (transaction_id, is_fraudulent, fraud_score, fraud_reason)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    is_fraudulent = VALUES(is_fraudulent),
                    fraud_score = VALUES(fraud_score),
                    fraud_reason = VALUES(fraud_reason),
                    labeled_at = CURRENT_TIMESTAMP
                """
                cursor.executemany(insert_query, labels)
                conn.commit()
                cursor.close()
                conn.close()
                
                fraud_percentage = (fraud_count / len(transactions) * 100) if transactions else 0
                print(f"✅ Labeled {len(transactions)} transactions")
                print(f"   - Fraudulent: {fraud_count} ({fraud_percentage:.1f}%)")
                print(f"   - Legitimate: {len(transactions) - fraud_count}")
                
                return {
                    'total_labeled': len(transactions),
                    'fraudulent': fraud_count,
                    'legitimate': len(transactions) - fraud_count
                }
                
            except Exception as e:
                print(f"❌ Error inserting fraud labels: {e}")
                raise
        
        # Main execution
        transactions = fetch_transaction_ids(logical_date)
        
        if transactions:
            return insert_fraud_labels(transactions)
        else:
            print("⚠️  No transactions found. Skipping fraud label generation.")
            return {'total_labeled': 0, 'fraudulent': 0, 'legitimate': 0}
    
    @task
    def pipeline_summary(**context):
        """
        Print pipeline execution summary.
        """
        ti = context['ti']
        
        txn_data = ti.xcom_pull(task_ids='generate_transaction_data')
        label_data = ti.xcom_pull(task_ids='generate_fraud_labels')
        
        print("=" * 60)
        print("🎉 FRAUD DETECTION DATA GENERATION COMPLETE")
        print("=" * 60)
        print(f"📊 Transactions Generated: {txn_data.get('total_transactions', 0)}")
        print(f"👥 Customers: {txn_data.get('num_customers', 0)}")
        print(f"🏷️  Labels Generated: {label_data.get('total_labeled', 0)}")
        print(f"🚨 Fraudulent: {label_data.get('fraudulent', 0)}")
        print(f"✅ Legitimate: {label_data.get('legitimate', 0)}")
        print("")
        print("📌 NEXT STEP:")
        print("   Go to Airbyte Cloud and manually trigger syncs:")
        print("   1. MySQL Connection → Sync Now")
        print("   2. PostgreSQL Connection → Sync Now")
        print("=" * 60)
        
        return {
            'status': 'success',
            'transactions': txn_data,
            'labels': label_data,
            'timestamp': datetime.now().isoformat()
        }
    
    # Pipeline dependencies
    txn_result = generate_transaction_data()
    label_result = generate_fraud_labels()
    summary = pipeline_summary()
    
    txn_result >> label_result >> summary


fraud_detection_pipeline()