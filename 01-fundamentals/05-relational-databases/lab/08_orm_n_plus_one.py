"""Block 8 · ORM and N+1 with SQLAlchemy (exercises 26–31).

Run from labs/sql-lab so db.py and models.py are importable:
    cd ~/Desktop/ROADMAP/labs/sql-lab
    PYTHONPATH=. uv run python ../../01-fundamentals/05-relational-databases/lab/08_orm_n_plus_one.py
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import aliased, contains_eager, joinedload, raiseload, selectinload

from db import Session, count_queries
from models import Category, Order, OrderItem, Product


def last_orders(session, *options):
    """Last 100 orders, optionally with loader options."""
    stmt = select(Order).order_by(Order.ordered_at.desc()).limit(100).options(*options)
    return session.scalars(stmt).all()


def ex26_customer_names() -> None:
    """26. Print the last 100 orders with the customer's name."""
    variants = {
        "lazy (default)": (),
        "joinedload": (joinedload(Order.customer),),
        "selectinload": (selectinload(Order.customer),),
    }
    for label, options in variants.items():
        with Session() as session, count_queries(label):  # new session = empty identity map
            for order in last_orders(session, *options):
                _ = f"{order.id} {order.customer.first_name} {order.customer.last_name}"
    # Result: lazy 98 queries (113 ms) · joinedload 1 (33 ms) · selectinload 2 (13 ms).
    # My predictions: 98 / 1 / 2 ✅.
    # Lazy = 1 query for the 100 orders + 1 per DISTINCT customer (97): the identity map keeps
    # objects already loaded in the session by PK, so repeated customers are not queried again.
    # selectinload = 2 separate round trips, both sent when the select runs (not on attribute access):
    # SELECT ... FROM orders LIMIT 100, then SELECT ... FROM customers WHERE id IN (...).
    # Rule of thumb: joinedload for many-to-one (order.customer), selectinload for collections.


def ex27_nested() -> None:
    """27. Nested N+1: order → items → product → category, for the last 100 orders."""
    variants = {
        "lazy (default)": (),
        "selectinload chain": (
            selectinload(Order.items)
            .joinedload(OrderItem.product)
            .joinedload(Product.category),
        ),
    }
    for label, options in variants.items():
        with Session() as session, count_queries(label):
            for order in last_orders(session, *options):
                for item in order.items:
                    _ = f"{order.id} {item.product.name} ({item.product.category.name})"
    # Result: lazy 366 queries (244 ms) · selectinload chain 2 queries (20 ms).
    # Lazy = 1 (orders) + 100 (items, one per ORDER) + 232 (distinct products) + 33 (distinct categories).
    # My prediction: 587 🟡 — products and categories ✅ (identity map), but a collection loads all
    # its rows in one query per parent: 100, not 321.
    # Optimized = 2: selectinload adds one query; chained joinedloads put their JOINs inside it.


def ex28_collection_limit() -> None:
    """28. joinedload on a collection (Order.items) + LIMIT: the last 5 orders with their items."""
    with Session() as session, count_queries("joinedload + limit"):
        stmt = (select(Order).order_by(Order.ordered_at.desc()).limit(5)
                .options(joinedload(Order.items)))
        orders = session.scalars(stmt).unique().all()  # unique() is required for joined collections
        print(f"  {len(orders)} orders, {sum(len(o.items) for o in orders)} items")
    # Hand-written SQL: orders JOIN order_items ... LIMIT 5 → 5 ROWS = only 2 orders (11459 ×3, 14775 ×2).
    # My prediction: fewer than 5 ✅. LIMIT cuts rows, not orders (fan-out breaking the limit).
    # SQLAlchemy wraps it: FROM (SELECT ... FROM orders ORDER BY ... LIMIT 5) AS anon_1
    #   LEFT OUTER JOIN order_items ... → 5 orders, 14 items, 1 query.
    # selectinload avoids the problem entirely (LIMIT on orders alone, then WHERE order_id IN (...)).


def ex29_raiseload() -> None:
    """29. raiseload("*"): any relationship not loaded up front raises instead of querying."""
    with Session() as session:
        stmt = (select(Order).order_by(Order.ordered_at.desc()).limit(3)
                .options(joinedload(Order.customer), raiseload("*")))
        order = session.scalars(stmt).first()
        print(f"  customer ok: {order.customer.first_name}")  # loaded with joinedload
        try:
            print(order.items)  # not loaded → raises
        except InvalidRequestError as exc:
            print(f"  items raised: {exc}")
    # Output: "customer ok: Johnny" · "items raised: 'Order.items' is not available due to lazy='raise'".
    # My prediction ✅: customer was loaded up front (joinedload); items was not → error, not a query.
    # Use it to fail fast: raiseload("*") per query, or lazy="raise" on the relationship so every
    # query must declare what it loads. A silent N+1 becomes an error in tests.


def ex30_contains_eager() -> None:
    """30. Orders from 2026-11-13 with Books items, loading ONLY those items."""
    parent = aliased(Category)

    def books_orders():
        return (
            select(Order)
            .join(Order.items).join(OrderItem.product).join(Product.category)
            .join(parent, Category.parent_id == parent.id)
            .where(parent.name == "Books",
                   Order.ordered_at >= datetime(2026, 11, 13, tzinfo=UTC),
                   Order.ordered_at < datetime(2026, 11, 14, tzinfo=UTC))
        )

    for label, option in {"selectinload": selectinload(Order.items),
                          "contains_eager": contains_eager(Order.items)}.items():
        with Session() as session, count_queries(label):
            orders = session.scalars(books_orders().options(option)).unique().all()
            print(f"  {label}: {len(orders)} orders, {sum(len(o.items) for o in orders)} items")
    # Result: selectinload 19 orders / 77 items (2 queries) · contains_eager 19 / 23 items (1 query).
    # My prediction: 77 ✅ — selectinload's own query is WHERE order_id IN (19 ids): it reuses the
    # filtered orders but not the Books condition, so it loads every item of those orders.
    # contains_eager fills order.items from the rows of MY join (already filtered).
    # Careful: order.items is now intentionally incomplete; don't reuse those objects as full orders.


def ex31_sales_per_month() -> None:
    """31. Exercise 8 (sales per month) with the ORM: Python loop vs aggregating in the database."""
    line_total = func.round(OrderItem.quantity * OrderItem.unit_price * (1 - OrderItem.discount), 2)

    # AI version: bring every row to Python and add it up there.
    with Session() as session, count_queries("python loop"):
        orders = session.scalars(
            select(Order).where(Order.status != "cancelled").options(selectinload(Order.items))
        ).all()
        totals: dict[str, Decimal] = defaultdict(Decimal)
        for order in orders:
            month = order.ordered_at.astimezone(UTC).strftime("%Y-%m")
            for item in order.items:
                totals[month] += round(item.quantity * item.unit_price * (1 - item.discount), 2)
        print(f"  python loop: {len(orders)} orders loaded, {len(totals)} months, "
              f"2025-11 = {totals['2025-11']}")

    # Database version: the database groups and sums, Python receives one row per month.
    with Session() as session, count_queries("func.sum + group_by"):
        month = func.date_trunc("month", Order.ordered_at).label("month")
        rows = session.execute(
            select(month,
                   func.count(func.distinct(Order.id)).label("orders_total"),
                   func.sum(line_total).label("total_sales"))
            .join(Order.items)
            .where(Order.status != "cancelled")
            .group_by(month)
            .order_by(month)
        ).all()
        nov = next(r for r in rows if r.month.strftime("%Y-%m") == "2025-11")
        print(f"  func.sum: {len(rows)} rows, 2025-11 = {nov.total_sales}")
    # Result: python loop 89 queries, 2,493 ms · func.sum 1 query, 125 ms (~20x). Same numbers:
    # 47 months, 2025-11 = 1,396,363.95 (matches exercise 8).
    # 89 = 1 (orders) + ceil(43,823 / 500) = 88 selectinload batches of WHERE order_id IN (500 ids).
    # The real cost is not the query count: ~44k orders + ~150k items cross the network and become
    # Python objects to produce 47 numbers. With 45M orders it would run out of memory. Trap 8.
    # Note: date_trunc uses the session time zone (exercise 22); the lab server runs in UTC.


if __name__ == "__main__":
    ex26_customer_names()
    ex27_nested()
    ex28_collection_limit()
    ex29_raiseload()
    ex30_contains_eager()
    ex31_sales_per_month()
