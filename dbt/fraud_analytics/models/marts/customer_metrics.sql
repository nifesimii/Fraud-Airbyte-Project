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
        t.transaction_id,
        t.amount,
        t.transaction_date,
        coalesce(f.is_fraudulent, false) as is_fraudulent
    from transactions t
    left join fraud_labels f
        on t.transaction_id = f.transaction_id
)

select
    user_id,
    count(transaction_id) as total_transactions,
    sum(amount) as total_amount,
    avg(amount) as avg_transaction_amount,
    min(transaction_date) as first_transaction,
    max(transaction_date) as last_transaction,
    count(case when is_fraudulent then 1 end) as fraud_count,
    round(
        count(case when is_fraudulent then 1 end)::float
        / nullif(count(transaction_id), 0) * 100, 2
    ) as fraud_rate_pct
from joined
group by user_id