"""SQLAlchemy 2.0 models for the Kestrel Market lab database.

schema.sql is the source of truth; these models only map the existing tables.
Every relationship uses the default lazy="select" loading on purpose, so the
classic N+1 problem shows up as soon as you iterate over related objects.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CHAR, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    def __repr__(self) -> str:
        label = getattr(self, "name", None) or getattr(self, "email", None) or ""
        return f"<{type(self).__name__} id={getattr(self, 'id', '?')} {label}>".replace(" >", ">")


# ───────────────────────── HR ─────────────────────────

class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]

    employees: Mapped[list[Employee]] = relationship(back_populates="department")


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    city: Mapped[str]
    state: Mapped[str] = mapped_column(CHAR(2))
    opened_at: Mapped[date]
    closed_at: Mapped[date | None]

    employees: Mapped[list[Employee]] = relationship(back_populates="store")
    orders: Mapped[list[Order]] = relationship(back_populates="store")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    email: Mapped[str]
    job_title: Mapped[str]
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id"))
    manager_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    salary: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    hire_date: Mapped[date]
    termination_date: Mapped[date | None]

    department: Mapped[Department] = relationship(back_populates="employees")
    store: Mapped[Store | None] = relationship(back_populates="employees")
    manager: Mapped[Employee | None] = relationship(back_populates="reports",
                                                    remote_side="Employee.id")
    reports: Mapped[list[Employee]] = relationship(back_populates="manager")
    orders: Mapped[list[Order]] = relationship(back_populates="employee")  # sales made in store


# ─────────────────────── Catalog ───────────────────────

class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))

    parent: Mapped[Category | None] = relationship(back_populates="children",
                                                   remote_side="Category.id")
    children: Mapped[list[Category]] = relationship(back_populates="parent")
    products: Mapped[list[Product]] = relationship(back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str]
    name: Mapped[str]
    brand: Mapped[str]
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    cost: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    discontinued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    category: Mapped[Category] = relationship(back_populates="products")
    order_items: Mapped[list[OrderItem]] = relationship(back_populates="product")


# ──────────────────────── Sales ────────────────────────

class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str]
    last_name: Mapped[str]
    email: Mapped[str]
    phone: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    addresses: Mapped[list[Address]] = relationship(back_populates="customer")
    orders: Mapped[list[Order]] = relationship(back_populates="customer")


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    street: Mapped[str]
    city: Mapped[str]
    state: Mapped[str] = mapped_column(CHAR(2))
    zip_code: Mapped[str]
    is_default: Mapped[bool]

    customer: Mapped[Customer] = relationship(back_populates="addresses")
    orders: Mapped[list[Order]] = relationship(back_populates="shipping_address")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    channel: Mapped[str]  # 'online' | 'in_store'
    store_id: Mapped[int | None] = mapped_column(ForeignKey("stores.id"))
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"))
    shipping_address_id: Mapped[int | None] = mapped_column(ForeignKey("addresses.id"))
    status: Mapped[str]  # 'pending' | 'paid' | 'shipped' | 'delivered' | 'cancelled'
    ordered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    customer: Mapped[Customer] = relationship(back_populates="orders")
    store: Mapped[Store | None] = relationship(back_populates="orders")
    employee: Mapped[Employee | None] = relationship(back_populates="orders")
    shipping_address: Mapped[Address | None] = relationship(back_populates="orders")
    items: Mapped[list[OrderItem]] = relationship(back_populates="order")
    payments: Mapped[list[Payment]] = relationship(back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    quantity: Mapped[int]
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    discount: Mapped[Decimal] = mapped_column(Numeric(3, 2))

    order: Mapped[Order] = relationship(back_populates="items")
    product: Mapped[Product] = relationship(back_populates="order_items")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    method: Mapped[str]
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    status: Mapped[str]  # 'completed' | 'failed' | 'refunded'
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    order: Mapped[Order] = relationship(back_populates="payments")
