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
        coalesce(f.is_fraudulent, false) as is_fraudulent
    from {{ source('staging', 'LABELED_TRANSACTIONS') }}
),

joined as (
    select
        t.user_id,
        count(t.transaction_id) as total_transactions,
        sum(t.amount) as total_amount,
        SUM(CASE WHEN f.is_fraudulent THEN 1 ELSE 0 END) AS fraudulent_transactions,
        SUM(CASE WHEN NOT f.is_fraudulent THEN 1 ELSE 0 END) AS non_frauduons,
        avg(t.amount) as avg_transaction_amount,
        min(t.transaction_date) as first_transaction,
        max(t.transaction_date) as last_transaction,
        count(case when f.is_fraudulent then 1 end) as fraud_count,
        round(
            count(case when f.is_fraudulent then 1 end)::float
            / nullif(count(t.transaction_id), 0) * 100, 2
        ) as fraud_rate_pct
    from transactions t
    left join fraud_labels f
        on t.transaction_id = f.transaction_id
    where user_id is not null
    GROUP BY  t.user_id
)

-- In the joined CTE, add a WHERE clause at the end:
select
    user_id,
    total_transactions,
    total_amount,
    fraudulent_transactions,
    non_fraudulent_transactions,
    (fraudulent_transactions::FLOAT/total_transactions) * 100 AS risk_score
    avg_transaction_amount,
    first_transaction,
    last_transaction,
    fraud_count,
    fraud_rate_pct
from joined
{# where user_id is not null
group by user_id #}