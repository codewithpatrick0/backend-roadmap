"""Quick check that the ORM mapping works and that count_queries() reports queries."""

from sqlalchemy import func, select

from db import Session, count_queries
from models import Customer, Employee, Order, Product

with Session() as session:
    for model in (Customer, Employee, Product, Order):
        total = session.scalar(select(func.count()).select_from(model))
        print(f"{model.__tablename__:<10} {total:>7,}")

    print()
    with count_queries("one order + lazy-loaded relations"):
        order = session.get(Order, 1)
        first_item = order.items[0]
        print(f"Order #{order.id} by {order.customer.first_name} {order.customer.last_name}: "
              f"{len(order.items)} items, first is {first_item.product.name!r} "
              f"({first_item.product.category.name})")
