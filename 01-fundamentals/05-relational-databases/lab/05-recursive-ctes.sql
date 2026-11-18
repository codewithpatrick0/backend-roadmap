-- Block 5 · Recursive CTEs (exercises 16–18)
-- Run: psql postgresql://lab:lab@localhost:5433/shop -f 05-recursive-ctes.sql
-- Quick mode: Claude writes the query, I predict the result and look for bugs.
-- Recursive CTE = anchor (runs once) UNION ALL recursive step (joins the CTE itself).
-- Each step only sees the rows added by the previous step; it stops when a step returns 0 rows.

-- 16. Full path of every category: Electronics > Accessories > Chargers & Cables.  → 44 rows
WITH RECURSIVE category_path AS (
    -- 1. Anchor: root categories
    SELECT id, name, parent_id, name AS path, 1 AS depth
    FROM categories
    WHERE parent_id IS NULL
    UNION ALL
    -- 2. Recursive step: children of the rows found in the previous step
    SELECT c.id, c.name, c.parent_id, cp.path || ' > ' || c.name, cp.depth + 1
    FROM categories c
    JOIN category_path cp ON c.parent_id = cp.id
)
SELECT id, path, depth
FROM category_path
ORDER BY path;
-- Predictions: all categories (not only leaves) ✅ 44 = 9 roots + children; Chargers & Cables
-- depth 3 ✅; stops when there are no more children ✅.
-- Lessons:
--   - A CTE works like a temporary table that only lives during the query.
--   - Each child inherits its parent's path and appends its own name → works at any depth
--     (exercise 9 used 3 fixed LEFT JOINs and breaks with a 4th level).
--   - `||` returns NULL if any part is NULL (CONCAT skips NULLs); safe here: name is NOT NULL.

-- 17. Org chart from the CEO with each employee's level.  → 244 rows (levels 1/2/3/4 = 1/9/71/163)
-- AI version joined `ON o.manager_id = e.id` → 1 row: it walks UP from the CEO, whose manager is NULL.
WITH RECURSIVE org AS (
    SELECT id, first_name, last_name, job_title, manager_id, 1 AS level
    FROM employees
    WHERE manager_id IS NULL
    UNION ALL
    SELECT e.id, e.first_name, e.last_name, e.job_title, e.manager_id, o.level + 1
    FROM employees e
    JOIN org o ON e.manager_id = o.id      -- fixed in review: the NEW row points to the row already found
)
SELECT level, id, first_name, last_name, job_title
FROM org
ORDER BY level, id;
-- Predictions: correct = 244 (all employees) ✅; this query = 1 ✅; bug = reversed join ✅.
-- Lesson: in the recursive step the parent column (manager_id / parent_id) belongs to the new alias.
--   Check: a full tree must return as many rows as the table (244 = count(*) FROM employees).

-- 18. Everyone who reports to the Head of Sales, directly or indirectly.  → 175 rows (12 + 163)
-- Written by me: same recursive step as 17, only the anchor changes.
WITH RECURSIVE org AS (
    SELECT id, first_name, last_name, job_title, manager_id, 1 AS level
    FROM employees
    WHERE job_title = 'Head of Sales'
    UNION ALL
    SELECT e.id, e.first_name, e.last_name, e.job_title, e.manager_id, o.level + 1
    FROM employees e
    JOIN org o ON e.manager_id  = o.id
)
SELECT level, id, first_name, last_name, job_title
FROM org
WHERE level <> 1
ORDER BY level, id;
-- Lessons:
--   - Change the anchor to start from any node; the recursive step stays the same.
--   - Exclude the root AFTER the recursion (final WHERE). Removing it from the anchor leaves
--     the recursion with nowhere to start → 0 rows.
--   - Filter by level, not by job_title again: it keeps working if the title changes.
--   - Level 2 = 12 Store Managers, level 3 = 163 sales associates (matches exercise 2b).
