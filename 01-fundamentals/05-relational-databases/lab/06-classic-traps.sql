-- Block 6 · Classic traps (exercises 19–22)
-- Run: psql postgresql://lab:lab@localhost:5433/shop -f 06-classic-traps.sql
-- Quick mode: Claude writes a query with a hidden bug, I predict the result and review it.

-- 19. Fan-out: items total and paid total per order in ONE query.  → 45,000 rows
-- AI version: orders JOIN order_items JOIN payments + SUM of both.
--   Order 103 (3 lines, 2 payments: failed + completed, real total 590.96):
--   3 × 2 = 6 rows before GROUP BY → items_total 1,181.92 (×2), paid_total 3,545.76 (×3 + failed).
--   Two bugs: fan-out (two 1:N joins multiply each other) + no status = 'completed'.
-- My first fix: `JOIN payments p ON p.order_id = o.id AND p.status = 'completed'`, GROUP BY o.id, p.amount.
--   Correct today (0 mismatches in 43,801 orders), but only because no order has 2 completed
--   payments — nothing in the schema enforces it (installments would break it). The inner join
--   also drops 1,199 orders with no completed payment (1,177 cancelled, 22 pending).
-- Robust fix: aggregate each child table first (1 row per order), then join 1:1.
WITH items AS (
    SELECT order_id, SUM(ROUND(quantity * unit_price * (1 - discount), 2)) AS items_total
    FROM order_items
    GROUP BY order_id                -- 1 row per order
),
paid AS (
    SELECT order_id, SUM(amount) AS paid_total
    FROM payments
    WHERE status = 'completed'
    GROUP BY order_id                -- 1 row per order
)
SELECT o.id, o.status, i.items_total, COALESCE(pd.paid_total, 0) AS paid_total
FROM orders o
JOIN items i      ON i.order_id = o.id
LEFT JOIN paid pd ON pd.order_id = o.id
ORDER BY o.id;
-- Lessons:
--   - SUM/COUNT/AVG run on the rows left AFTER the joins, not on the original tables.
--   - Aggregate before you join. Each CTE is a temporary, already-summarised table.
--   - Write for the business rule, not for today's data (same lesson as exercise 2b).

-- 20. Employees who never made a sale.  → 76 rows
-- AI version: WHERE id NOT IN (SELECT employee_id FROM orders) → 0 rows, no error.
--   28,123 online orders have employee_id NULL, and
--   x NOT IN (1, 2, NULL) = x <> 1 AND x <> 2 AND x <> NULL → ... AND NULL → never TRUE.
SELECT e.id, e.first_name, e.last_name, e.job_title
  FROM employees e
  WHERE NOT EXISTS (
      SELECT 1 FROM orders WHERE employee_id  = e.id
  )
;
-- Lessons:
--   - NOT EXISTS ignores NULLs (NULL = e.id is never true), so it is safe by default.
--   - NOT IN (... WHERE employee_id IS NOT NULL) also gives 76, but relies on remembering the filter.
--   - Review note: alias the subquery column (o.employee_id) — trap 10.
--   - 7 sales associates with a store never sold anything: worth asking why.

-- 21. COUNT(*) vs COUNT(column) vs COUNT(DISTINCT column).  → 5,000 / 4,258 / 4,142
-- AI version: customers LEFT JOIN orders + COUNT(*), COUNT(c.phone), COUNT(DISTINCT o.customer_id)
--   → 45,858 / 39,822 / 4,142. Only the DISTINCT column was right.
-- My prediction: "looks right" ❌ — I knew what each COUNT does but missed the grain:
--   after the 1:N join each row is an ORDER (45,000) + 1 row per customer with no orders (858).
-- Fix B (preferred): no join, so rows never multiply.
SELECT COUNT(*)     AS total_customers,
       COUNT(phone) AS customers_with_phone,
       COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM orders o WHERE o.customer_id = c.id))
                    AS customers_who_bought
FROM customers c;
-- Fix A: keep the join and count DISTINCT c.id (with FILTER for the phone column).
-- Lessons:
--   - COUNT(*) = rows; COUNT(col) = non-NULL values; COUNT(DISTINCT col) = distinct non-NULL values.
--   - After a 1:N join, any COUNT on the parent table without DISTINCT is suspicious.
--   - FILTER (WHERE ...) applies a condition to one aggregate only.

-- 22. "Yesterday's" orders (today = 2026-11-13, manager in Lima, UTC-5).  → 63
-- AI version: WHERE ordered_at::date = date '2026-11-12'
--   ::date converts with the SESSION time zone: UTC → 69, America/Lima → 63, Asia/Tokyo → 66.
-- My prediction ✅: in Lima it goes down; order 19756 (2026-11-12 00:35 UTC) is Nov 11, 19:35 in Lima.
--   The day window shifts 5 hours: 16 orders leave (Nov 12 00–05 UTC), 10 enter (Nov 13 00–05 UTC).
-- Fix: put the time zone in the filter itself → 63 in any session.
SELECT count(*) AS orders_yesterday
FROM orders
WHERE ordered_at >= timestamptz '2026-11-12 00:00 America/Lima'
  AND ordered_at <  timestamptz '2026-11-13 00:00 America/Lima';
-- Also correct: (ordered_at AT TIME ZONE 'America/Lima')::date = date '2026-11-12'.
-- The range is preferred: half-open interval + it can use an index on ordered_at (block 7);
-- wrapping the column in a function/cast prevents that.
