-- Block 2b · Independent practice: "Who sold outside their team?"
-- In-store sales where the seller and their manager do NOT work in the same store.  → 1,666 rows

SELECT o.id, s.name, e.job_title, CONCAT(e.first_name, ' ', e.last_name) AS employee_fullname,
CONCAT(m.first_name, ' ', m.last_name) AS manager_fullname,
e.store_id AS employee_store, m.store_id AS manager_store FROM orders o
JOIN stores s ON s.id = o.store_id
JOIN employees e ON e.id = o.employee_id
JOIN employees m ON m.id = e.manager_id
WHERE m.store_id IS DISTINCT FROM e.store_id AND o.channel = 'in_store'
;

-- What I learned:
--   - `<>` returned 0 rows: 3 <> NULL is NULL, not true. IS DISTINCT FROM treats NULL as a value.
--     (`<> … OR m.store_id IS NULL` works too, but misses the case e.store_id IS NULL.)
--   - Copy-paste bug in my first try: manager_fullname used e. instead of m. (no error, wrong data).
--   - Everyone in the result is a Store Manager (12 people) reporting to #2, Head of Sales,
--     who works at headquarters (store_id NULL). Sales Associates report to a manager in
--     their own store, so they never appear.
--   - Today no manager works in a *different store*, so `<>` adds no rows. I keep the rule
--     anyway: write the query for the business rule, not for the data I see today.
