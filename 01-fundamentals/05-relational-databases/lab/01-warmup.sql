-- Block 1 · Warm-up (exercises 1–3)
-- Run: psql postgresql://lab:lab@localhost:5433/shop -f 01-warmup.sql

-- 1. The 10 most expensive products with their category.
SELECT p.name  AS product,
       p.price,
       c.name  AS category
FROM products p
JOIN categories c ON c.id = p.category_id
ORDER BY p.price DESC
LIMIT 10;
-- Note: if the 10th and 11th had the same price, LIMIT would drop one at random.
-- `FETCH FIRST 10 ROWS WITH TIES` keeps both.

-- 2. Customers registered in 2024 without a phone.  → 179 rows
SELECT first_name, last_name, email, created_at
FROM customers
WHERE phone IS NULL
  AND created_at >= '2024-01-01'   -- half-open interval: [start, end)
  AND created_at <  '2025-01-01';
-- Mistakes in my first attempt:
--   - Missing `phone IS NULL` (returned all 1,110 customers of 2024).
--   - `> '2024-01-01'` dropped 2024-01-01 00:00:00; `<= '2025-01-01'` included it.

-- 3. Active employees today in each store.
SELECT s.name     AS store,
       s.closed_at,
       count(e.id) AS active_employees     -- count(e.id), not count(*): 0 instead of 1
FROM stores s
LEFT JOIN employees e
       ON e.store_id = s.id
      AND e.termination_date IS NULL       -- in ON, not WHERE: keeps stores with 0
GROUP BY s.id, s.name, s.closed_at
ORDER BY active_employees DESC;
-- Mistake in my first attempt: grouped by department instead of store.
-- Headquarters (store_id IS NULL) has 56 more active employees that are not in any store.
