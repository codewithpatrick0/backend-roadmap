-- Block 7 · Performance and indexes (exercises 23–25)
-- Run: psql postgresql://lab:lab@localhost:5433/shop -f 07-performance.sql
-- EXPLAIN shows the plan; EXPLAIN ANALYZE also runs the query and measures it.
-- Note: CREATE INDEX changes the lab database (it persists in the sql-lab_pgdata volume).

-- 23. All orders of customer 42.  → 17 rows
EXPLAIN ANALYZE SELECT * FROM orders WHERE customer_id = 42;
-- Before (only orders_pkey exists):
--   Seq Scan on orders · Rows Removed by Filter: 44983 · 512 pages · Execution Time: 4.449 ms
CREATE INDEX IF NOT EXISTS orders_customer_id_idx ON orders (customer_id);
EXPLAIN ANALYZE SELECT * FROM orders WHERE customer_id = 42;
-- After:
--   Bitmap Index Scan on orders_customer_id_idx → Bitmap Heap Scan · 17 pages · 0.047 ms (~95x)
--   Index size: 416 kB.
-- My predictions:
--   1. It read all 45,000 rows ✅ — correction: without an index a Seq Scan ALWAYS reads the whole
--      table; the filter only decides which rows to keep.
--   2. "A faster seq scan" 🟡 — the node itself changes: Bitmap Index Scan + Bitmap Heap Scan.
--   3. "4 ms is not worth it" → changed my mind ✅: Seq Scan grows with the table (45M rows ≈ 1000x),
--      a B-tree lookup barely grows. And 4 ms × 1,000 requests/s adds up.
-- Lessons:
--   - PostgreSQL does NOT index foreign keys automatically (MySQL/InnoDB does). Trap 2.
--   - Index cost: disk space + slower INSERT/UPDATE. Index what you filter or join on often.
--   - Seq Scan on a big table in a plan = likely a missing index.

-- 24. All sales of product 42 in order_items (151,455 rows).  → 272 rows
EXPLAIN ANALYZE SELECT * FROM order_items WHERE product_id = 42;
-- Before: Index Scan using order_items_order_id_product_id_key · ~3.9 ms (same as a forced Seq Scan).
--   AI review said "it already uses an Index Scan, no index needed" ❌.
--   The unique index is (order_id, product_id): sorted by order_id first, so product_id = 42 is
--   scattered across the whole index → PostgreSQL walks all of it. (First run, cold cache: 20.7 ms.)
CREATE INDEX IF NOT EXISTS order_items_product_id_idx ON order_items (product_id);
EXPLAIN ANALYZE SELECT * FROM order_items WHERE product_id = 42;
-- After: Bitmap Index Scan on order_items_product_id_idx → ~0.7–1.1 ms (~4x). Size: 1,072 kB.
--   Smaller gain than exercise 23: 272 rows spread over many pages vs 17 rows.
-- Reading a plan: cost = estimate in internal units (not ms); rows = estimated rows;
--   actual time = first row..last row in ms; actual rows = real rows (66 estimated vs 272 real).
-- Lessons:
--   - Leftmost prefix rule: an index on (a, b) helps WHERE a = … or a = … AND b = …, not b alone.
--   - "Index Scan" in a plan is not proof the index helps: check actual time and the index columns.
-- Which other FKs need an index? My pick: payments.order_id ✅ (hot path: every time an order is opened).
CREATE INDEX IF NOT EXISTS payments_order_id_idx ON payments (order_id);
--   Order 103: Seq Scan 7.4 ms → Index Scan 0.18 ms (~40x).
--   employees.manager_id: 244 rows in 4 pages → a Seq Scan is already instant. Index big or hot tables first.
--   Still without index: orders.store_id / employee_id / shipping_address_id, products.category_id,
--   employees.* (small table).

-- 25. pg_stat_statements after running the ORM script (lab/08_orm_n_plus_one.py).
-- The lab server already loads it (docker-compose: shared_preload_libraries=pg_stat_statements).
SELECT pg_stat_statements_reset();
-- ...run: PYTHONPATH=. uv run python ../../01-fundamentals/05-relational-databases/lab/08_orm_n_plus_one.py
SELECT calls, round(total_exec_time::numeric, 1) AS total_ms, rows,
       left(regexp_replace(query, '\s+', ' ', 'g'), 100) AS query
FROM pg_stat_statements
WHERE query NOT ILIKE '%pg_stat_statements%'
ORDER BY calls DESC
LIMIT 6;
-- Result: products WHERE id = $1 → 232 calls / 232 rows; customers → 97 / 97; categories → 33 / 33;
--   order_items WHERE order_id = $1 → 100 calls (lazy collections); order_items IN (...) → 105,672 rows.
-- N+1 fingerprint: the same query, many calls, ~1 row per call (calls ≈ rows), filtered by id = $1.
--   232 and 33 come from exercise 27 (products, categories), 97 from exercise 26 (customers).
-- Sort by total_exec_time instead of calls to find the most expensive query.
