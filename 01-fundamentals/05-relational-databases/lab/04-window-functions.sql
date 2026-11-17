-- Block 4 · Window functions (exercises 12–15)
-- Run: psql postgresql://lab:lab@localhost:5433/shop -f 04-window-functions.sql
-- Window function = calculates over a group of rows WITHOUT collapsing them (unlike GROUP BY).

-- 12. Ranking of sellers within each store.  → 168 rows
-- First try (works): GROUP BY employee_fullname, e.store_id + RANK() OVER (... ORDER BY SUM(...) DESC).
-- Fixed in review: group by the PK (e.id) — two sellers with the same name would be merged;
-- alias for the rank column; final ORDER BY (the ORDER BY inside OVER does not sort the output).
WITH seller_sales AS (
    SELECT e.id,
           CONCAT(e.first_name, ' ', e.last_name)                         AS employee_fullname,
           e.store_id,
           SUM(ROUND(oi.quantity * oi.unit_price * (1 - oi.discount), 2)) AS sales_total
    FROM orders o
    JOIN employees e    ON e.id = o.employee_id
    JOIN order_items oi ON oi.order_id = o.id
    GROUP BY e.id, e.first_name, e.last_name, e.store_id
)
SELECT store_id, employee_fullname, sales_total,
       RANK() OVER (PARTITION BY store_id ORDER BY sales_total DESC) AS rank_in_store
FROM seller_sales
ORDER BY store_id, rank_in_store;
-- RANK: ties share a place and skip numbers (1,1,3). DENSE_RANK: 1,1,2. ROW_NUMBER: 1,2,3 (random tie-break).

-- 13. Running total of sales, day by day, November 2025 (company-wide).  → 30 rows
SELECT SUM(p.amount) AS total,
SUM(SUM(p.amount)) OVER (ORDER BY date_trunc('day', o.ordered_at)) AS acumulado,
date_trunc('day', o.ordered_at) AS day FROM payments p
JOIN orders o ON p.order_id = o.id
WHERE o.ordered_at >= '2025-11-01 00:00:00' AND o.ordered_at < '2025-12-01 00:00:00'
AND p.status = 'completed'
GROUP BY day
ORDER by day ASC;
-- Validation: last running total = 1,396,363.95 = November 2025 in exercise 8 (via order_items).
-- Lessons:
--   - Inner SUM = daily total (GROUP BY); outer SUM ... OVER (ORDER BY day) = running total.
--   - SELECT aliases can't be used inside OVER (...): "column day does not exist".
--   - Filter and group by the SAME date. Filtering by paid_at and grouping by ordered_at
--     added an Oct 31 row and dropped Nov 30 orders paid on Dec 1.
--   - ordered_at = sales (when the customer bought); paid_at = income (when the money came in).

-- 14. Time between consecutive orders of each customer (LAG).  → 45,000 rows
SELECT t.customer_id, t.id AS order_id, t.customer_fullname,
t.previous_order_at , t.ordered_at,
t.ordered_at - t.previous_order_at AS elapsed_time
FROM (
    SELECT o.customer_id, o.id, o.ordered_at, LAG(o.ordered_at) OVER (PARTITION BY o.customer_id ORDER BY o.ordered_at) AS previous_order_at,
    CONCAT(c.first_name, ' ', c.last_name) AS customer_fullname
    FROM orders o
    JOIN customers c ON c.id = o.customer_id
    ) t
    ORDER BY t.customer_id, t.ordered_at
;
-- Lessons:
--   - LAG(x) OVER (PARTITION BY customer ORDER BY date) = value of the previous row in the group.
--     First order of each customer → NULL (4,142 NULLs = 4,142 customers).
--   - interval (timestamp - timestamp) instead of whole days (date - date): 1,332 gaps are under
--     1 day, and ::date would show them as 0 or 1. Same order, two answers: 503 days 15:29 vs 504.
--   - Subquery on purpose: LAG is written once (DRY) and the outer query can filter by
--     elapsed_time (window functions run after WHERE, so WHERE LAG(...) is not allowed).
--   - Smallest gap = 37 seconds → likely a double submit. Good data-quality check.

-- 15. TODO: margin per product and its percentile within its category.
