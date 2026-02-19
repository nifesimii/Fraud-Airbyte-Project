{{ config(materialized='table') }}

with transactions as (
    select
        transaction_id,
        user_id,
        amount,
        transaction_date
    from {{ source('staging', 'CUSTOMER_TRANSACTIONS') }}
),

fraud_labels as (
    select
        transaction_id,
        is_fraudulent
    from {{ source('staging', 'LABELED_TRANSACTIONS') }}
),

joined as (
    select
        t.user_id,
        count(t.transaction_id) as total_transactions,
        sum(t.amount) as total_amount,
        sum(case when f.is_fraudulent then 1 else 0 end) as fraudulent_transactions,
        sum(case when not f.is_fraudulent then 1 else 0 end) as non_fraudulent_transactions,
        avg(t.amount) as avg_transaction_amount,
        min(t.transaction_date) as first_transaction,
        max(t.transaction_date) as last_transaction
    from transactions t
    left join fraud_labels f
        on t.transaction_id = f.transaction_id
    where t.user_id is not null
    group by t.user_id
)

select
    user_id,
    total_transactions,
    total_amount,
    fraudulent_transactions,
    non_fraudulent_transactions,
    round(fraudulent_transactions::float / nullif(total_transactions, 0) * 100, 2) as fraud_rate_pct,
    avg_transaction_amount,
    first_transaction,
    last_transaction
from joined