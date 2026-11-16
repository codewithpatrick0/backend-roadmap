-- Block 2 · JOINs (exercises 4–7)
-- Run: psql postgresql://lab:lab@localhost:5433/shop -f 02-joins.sql

-- 4a. Customers who never bought (LEFT JOIN … IS NULL).  → 858 rows
SELECT c.id,
       CONCAT(c.first_name, ' ', c.last_name) AS customer_fullname
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id
WHERE o.id IS NULL;   -- check a NOT NULL column (PK); a nullable one like o.store_id would lie

-- 4b. Same with NOT EXISTS (both become a "Hash Anti Join" in EXPLAIN).  → 858 rows
SELECT c.id,
       CONCAT(c.first_name, ' ', c.last_name) AS customer_fullname
FROM customers c
WHERE NOT EXISTS (
    SELECT 1 FROM orders o
    WHERE o.customer_id = c.id
);
-- Open question: if all of a customer's orders are cancelled, did they buy? (→ 871)

-- 5. Products never sold.  → 2 rows
SELECT p.id, p.name
FROM products p
WHERE NOT EXISTS (
    SELECT 1 FROM order_items oi
    WHERE oi.product_id = p.id
);
-- Why: #1467 was discontinued (2022-11-13) before the first order (Jan 2023).

-- 6. Each employee with their manager (self-join).  → 244 rows (243 with INNER JOIN)
SELECT CONCAT(e.first_name, ' ', e.last_name)                 AS employee,
       COALESCE(m.first_name || ' ' || m.last_name, '(no manager)') AS manager
FROM employees e
LEFT JOIN employees m ON e.manager_id = m.id;
-- The CEO has manager_id NULL; NULL = m.id is never true, so INNER JOIN drops her.
-- CONCAT(NULL, ' ', NULL) returns ' ' (not NULL) → use || + COALESCE.

-- 7. Online orders shipped to a state different from the customer's default address.  → 1,488 rows
SELECT o.id,
       o.customer_id,
       o.channel,
       oa.state AS order_state,
       da.state AS default_state
FROM orders o
JOIN addresses oa ON o.shipping_address_id = oa.id       -- 1 row: where it was shipped
JOIN addresses da ON o.customer_id = da.customer_id      -- 1 row: the customer's default…
                 AND da.is_default                       -- …without this, one row per address (fan-out)
WHERE oa.state <> da.state;
-- In-store orders have shipping_address_id NULL, so the first JOIN already drops them.
