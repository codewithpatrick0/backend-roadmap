-- Block 6b · Review round: new exercises, same mistakes as 15, 19 and 21
-- Run: psql postgresql://lab:lab@localhost:5433/shop -f 06b-review.sql
-- Quick mode: Claude wrote a buggy query, I predicted the result and proposed a fix.

-- R1. Addresses and orders per customer (two 1:N children, like exercise 19).  → 5,000 rows
-- AI version: customers JOIN addresses JOIN orders + COUNT(a.id), COUNT(o.id).
--   Customer 77 (3 addresses, 4 orders): 3 × 4 = 12 rows, each = one address COMBINED with one order
--   → 12 and 12. Two counts from different tables giving the same number = fan-out red flag.
--   Also: INNER joins drop customers with no address (256) or no orders (858) → 3,932 of 5,000.
-- My fix: COUNT(DISTINCT ...) ✅ (safe here: it counts PKs, which are unique). Added LEFT JOIN.
SELECT c.id,
       COUNT(DISTINCT a.id) AS addresses,
       COUNT(DISTINCT o.id) AS orders
FROM customers c
LEFT JOIN addresses a ON a.customer_id = c.id
LEFT JOIN orders o    ON o.customer_id = c.id
GROUP BY c.id
ORDER BY c.id;

-- R2. Total products and discontinued products (COUNT after LEFT JOIN, like exercise 21).  → 1,500 / 113
-- AI version: products LEFT JOIN order_items + COUNT(*), COUNT(p.discontinued_at) → 151,457 / 5,725.
-- My fix: DISTINCT order_id ❌ — the repeated thing is the PRODUCT (one row per sale), not the order.
-- Better: the join is not needed at all (YAGNI).
SELECT COUNT(*)               AS total_products,
       COUNT(discontinued_at) AS discontinued_products
FROM products;

-- R3. Best-paid employee of each department (missing PARTITION BY, like exercise 15).  → 8 rows
-- AI version: RANK() OVER (ORDER BY salary DESC) → 1 row (the CEO). Bug, not improvement.
-- My fix added PARTITION BY ✅ but removed WHERE salary_rank = 1 ❌ → 244 rows (everyone ranked).
SELECT id, first_name, last_name, department_id, salary
FROM (
    SELECT e.*, RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) AS salary_rank
    FROM employees e
) ranked
WHERE salary_rank = 1
ORDER BY department_id;
-- Note: subquery alias (ranked) is optional since PostgreSQL 16, required before and in MySQL.
-- Department 5 (IT): the top earner is a Software Engineer, not the Head of IT.

-- R4. Fixing fan-out with SUM(DISTINCT ...) (fix that depends on the data, like exercise 19).
-- AI version: orders JOIN order_items JOIN payments + SUM(DISTINCT line_total).
--   DISTINCT removes repeated VALUES, not repeated rows: order 1069 (18.99 + 18.99) → 18.99, not 37.98.
--   Wrong in 568 orders, $24,141.28 missing. Order 103 looked fine, so a quick test would pass.
-- My review ✅: same values get merged; the payments join is not used → remove it, plain SUM.
SELECT order_id, SUM(ROUND(quantity * unit_price * (1 - discount), 2)) AS items_total
FROM order_items
GROUP BY order_id
ORDER BY order_id;
-- Using payments.amount instead answers another question (charged ≠ sold): 621 orders have no
-- payment, it needs status = 'completed', and installments would bring the fan-out back.

-- Takeaways:
--   - Before fixing a join, ask whether the join is needed at all.
--   - DISTINCT is a safe fix only on unique keys (ids), never on amounts.
--   - After a fix, check that the query still answers the original question.
