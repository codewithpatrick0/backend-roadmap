-- Block 3 · Aggregations (exercises 8–11)
-- Run: psql postgresql://lab:lab@localhost:5433/shop -f 03-aggregations.sql

-- 8. Total sales per month.
SELECT date_trunc('month', o.ordered_at)                              AS month,
       COUNT(DISTINCT o.id)                                           AS orders_total,  -- fixed in review: COUNT(o.id) counted order lines (fan-out: 3,162 vs 919 in Nov 2026)
       SUM(ROUND(oi.quantity * oi.unit_price * (1 - oi.discount), 2)) AS total_sales    -- round each line, then sum
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
WHERE o.status <> 'cancelled'      -- fixed in review: cancelled orders were never charged
GROUP BY month
ORDER BY month;
-- Lesson: after the JOIN the grain is "one row per order item", not "one row per order".

-- 9. Sales per section (category tree with mixed depth: 2 or 3 levels).  → 9 rows
SELECT (SUM(ROUND(oi.quantity * oi.unit_price * (1 - oi.discount), 2))) AS product_sales,
COALESCE(spc.name, pc.name, c.name) AS category FROM order_items oi
JOIN products p ON oi.product_id = p.id
LEFT JOIN categories c ON p.category_id = c.id
LEFT JOIN categories pc ON c.parent_id = pc.id
LEFT JOIN categories spc ON spc.id = pc.parent_id      -- LEFT: level-2 products have no grandparent
JOIN orders o ON o.id = oi.order_id                    -- child → parent: no fan-out
WHERE o.status <> 'cancelled'
GROUP BY COALESCE(spc.name, pc.name, c.name)
ORDER BY 1 DESC;
-- Mistakes on the way:
--   - INNER JOIN to the grandparent kept only Electronics (15,902 of 151,455 lines).
--   - ROUND(SUM(x)) ≠ SUM(ROUND(x)): $8.19 off in Electronics. Round where money is charged.
--   - Selecting c.name while grouping by the COALESCE fails: 8 leaf names per section.
-- Limitation: hardcoded depth (max 3 levels). A recursive CTE handles any depth (block 5).

-- 10. Average ticket (order total) per channel and payment method.
SELECT ROUND(AVG(p.amount), 2) AS avg_amount, o.channel, p.method FROM orders o
JOIN payments p ON o.id = p.order_id
WHERE p.status = 'completed'       -- fixed in review: `<> 'failed'` let 578 refunded payments in (allowlist > denylist)
GROUP BY o.channel, p.method
ORDER BY o.channel, p.method;
-- Lessons:
--   - AVG(oi.unit_price) is the average product price (~$183), not the average ticket (~$816).
--   - payments.amount of the completed payment = order total, so order_items is not needed.

-- 11. Top 5 stores by sales in 2025.
SELECT s.name AS store_name, SUM(ROUND(oi.quantity * oi.unit_price * (1 - oi.discount), 2)) as sales_total,
date_trunc('year', ordered_at) AS year
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
JOIN stores s ON o.store_id = s.id
WHERE o.ordered_at >= '2025-01-01 00:00:00' AND o.ordered_at < '2026-01-01 00:00:00'
GROUP BY year, s.name
ORDER BY sales_total DESC
LIMIT 5;
-- Lessons:
--   - "Most sales" = revenue, not order count: ranking by COUNT swaps Denver/Nashville for Austin/Phoenix.
--   - Same totals to the cent as SUM(payments.amount) → cross-validation of both paths.
--   - Portland is included (it sold Jan–Jun 2025) but ranks 12th: half a year is apples to oranges.
