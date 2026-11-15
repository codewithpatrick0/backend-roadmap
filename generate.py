#!/usr/bin/env python3
"""Build the Kestrel Market lab database: a coherent, reproducible fictional dataset.

Drops everything, recreates the schema from schema.sql, loads the data with COPY
and runs coherence checks. Safe to re-run at any time (same seed = same data).

    uv run python generate.py
"""

from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from itertools import accumulate
from pathlib import Path

import psycopg
from faker import Faker

DSN = os.environ.get("LAB_DSN", "postgresql://lab:lab@localhost:5433/shop")
SEED = 42

N_CUSTOMERS = 5_000
N_PRODUCTS = 1_500
N_ORDERS = 45_000

UTC = timezone.utc
COMPANY_START = date(2019, 1, 2)
ORDERS_START = datetime(2023, 1, 1, tzinfo=UTC)
NOW = datetime(2026, 11, 13, 22, 0, tzinfo=UTC)  # the dataset's frozen "today"
TODAY = NOW.date()

CENT = Decimal("0.01")
rng = random.Random(SEED)
fake = Faker("en_US")
fake.seed_instance(SEED)


# ───────────────────────── helpers ─────────────────────────

def trunc(dt: datetime) -> datetime:
    return dt.replace(microsecond=0)


def rand_date(start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, (end - start).days))


def rand_dt(start: datetime, end: datetime) -> datetime:
    return trunc(start + (end - start) * rng.random())


def at_midnight(d: date) -> datetime:
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def salary(lo: int, hi: int) -> Decimal:
    return Decimal(rng.randrange(lo, hi + 1, 500))


def slug(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum())


_used_emails: set[str] = set()


def unique_email(local: str, domain: str) -> str:
    email, n = f"{local}@{domain}", 1
    while email in _used_emails:
        n += 1
        email = f"{local}{n}@{domain}"
    _used_emails.add(email)
    return email


def ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


# ───────────────────────── reference data ─────────────────────────

# (city, state). Every city really is in that state, so addresses stay coherent.
CITIES = [
    ("New York", "NY"), ("Brooklyn", "NY"), ("Buffalo", "NY"), ("Los Angeles", "CA"),
    ("San Francisco", "CA"), ("San Diego", "CA"), ("Sacramento", "CA"), ("Chicago", "IL"),
    ("Springfield", "IL"), ("Houston", "TX"), ("Austin", "TX"), ("Dallas", "TX"),
    ("San Antonio", "TX"), ("Phoenix", "AZ"), ("Tucson", "AZ"), ("Philadelphia", "PA"),
    ("Pittsburgh", "PA"), ("Seattle", "WA"), ("Spokane", "WA"), ("Denver", "CO"),
    ("Boston", "MA"), ("Atlanta", "GA"), ("Miami", "FL"), ("Orlando", "FL"), ("Tampa", "FL"),
    ("Portland", "OR"), ("Minneapolis", "MN"), ("Detroit", "MI"), ("Nashville", "TN"),
    ("Charlotte", "NC"), ("Raleigh", "NC"), ("Columbus", "OH"), ("Cleveland", "OH"),
    ("Las Vegas", "NV"), ("Salt Lake City", "UT"),
]

# (city, state, opened_at, closed_at)
STORES = [
    ("Austin", "TX", date(2019, 3, 15), None),
    ("Dallas", "TX", date(2019, 9, 2), None),
    ("Houston", "TX", date(2020, 2, 10), None),
    ("Chicago", "IL", date(2020, 6, 1), None),
    ("Denver", "CO", date(2020, 11, 5), None),
    ("Phoenix", "AZ", date(2021, 4, 20), None),
    ("Seattle", "WA", date(2021, 8, 14), None),
    ("Atlanta", "GA", date(2022, 1, 10), None),
    ("Miami", "FL", date(2022, 5, 2), None),
    ("Portland", "OR", date(2022, 9, 19), date(2025, 6, 30)),  # closed store
    ("Boston", "MA", date(2023, 3, 6), None),
    ("Nashville", "TN", date(2024, 2, 12), None),
]

DEPARTMENTS = ["Executive", "Sales", "Customer Service", "Marketing", "IT",
               "Finance", "Human Resources", "Logistics"]

# Headquarters staff per department: ([(title, min salary, max salary)], headcount)
HQ_STAFF = {
    "Executive": ([("Executive Assistant", 55_000, 70_000)], 2),
    "Customer Service": ([("Customer Service Agent", 36_000, 46_000),
                          ("Senior Customer Service Agent", 44_000, 55_000)], 14),
    "Marketing": ([("Marketing Specialist", 52_000, 72_000), ("Content Writer", 48_000, 65_000),
                   ("SEO Analyst", 55_000, 78_000)], 8),
    "IT": ([("Software Engineer", 85_000, 140_000), ("Data Analyst", 65_000, 95_000),
            ("IT Support Technician", 45_000, 62_000)], 10),
    "Finance": ([("Accountant", 55_000, 80_000), ("Financial Analyst", 62_000, 92_000)], 6),
    "Human Resources": ([("HR Generalist", 50_000, 70_000), ("Recruiter", 48_000, 68_000)], 5),
    "Logistics": ([("Warehouse Associate", 34_000, 44_000),
                   ("Logistics Coordinator", 46_000, 62_000)], 16),
}

# Category tree. A dict is an inner category; a tuple is a leaf: (nouns, (min price, max price)).
# Depth is mixed on purpose: Electronics > Smartphones vs Electronics > Audio > Headphones.
CATALOG = {
    "Electronics": {
        "Smartphones": (["Smartphone"], (199, 1299)),
        "Laptops": (["Laptop", "Ultrabook", "Chromebook"], (299, 2499)),
        "Tablets": (["Tablet", "E-Reader"], (99, 1099)),
        "Audio": {
            "Headphones": (["Wireless Earbuds", "Over-Ear Headphones",
                            "Noise-Cancelling Headphones"], (25, 399)),
            "Speakers": (["Bluetooth Speaker", "Soundbar", "Smart Speaker"], (35, 599)),
        },
        "Smart Home": (["Smart Plug", "Video Doorbell", "Smart Thermostat",
                        "Security Camera", "Smart Bulb"], (15, 249)),
        "Accessories": {
            "Chargers & Cables": (["USB-C Charger", "Charging Cable", "Power Bank",
                                   "Wireless Charger"], (9, 89)),
            "Cases & Protection": (["Phone Case", "Laptop Sleeve", "Screen Protector",
                                    "Tablet Cover"], (9, 59)),
        },
    },
    "Home & Kitchen": {
        "Cookware": (["Frying Pan", "Saucepan", "Dutch Oven", "Knife Set", "Baking Sheet"], (15, 249)),
        "Small Appliances": (["Blender", "Air Fryer", "Coffee Maker", "Toaster", "Stand Mixer"],
                             (25, 449)),
        "Furniture": (["Bookshelf", "Coffee Table", "Desk Chair", "TV Stand", "Nightstand"],
                      (59, 899)),
        "Bedding": (["Comforter", "Sheet Set", "Pillow", "Weighted Blanket"], (19, 199)),
    },
    "Sports & Outdoors": {
        "Fitness": (["Yoga Mat", "Dumbbell Set", "Resistance Bands", "Kettlebell", "Jump Rope"],
                    (9, 299)),
        "Camping": (["Tent", "Sleeping Bag", "Camping Stove", "Headlamp", "Backpack"], (15, 449)),
        "Cycling": (["Bike Helmet", "Bike Lock", "Cycling Gloves", "Bike Light"], (12, 149)),
    },
    "Clothing": {
        "Men": (["T-Shirt", "Hoodie", "Jeans", "Jacket", "Polo Shirt"], (15, 149)),
        "Women": (["Blouse", "Dress", "Leggings", "Cardigan", "Jacket"], (15, 149)),
        "Kids": (["Kids T-Shirt", "Kids Pajamas", "Kids Jacket", "Kids Hoodie"], (9, 69)),
        "Shoes": (["Running Shoes", "Sneakers", "Hiking Boots", "Sandals"], (29, 199)),
    },
    "Books": {
        "Fiction": ([], (9, 29)),
        "Non-Fiction": ([], (12, 35)),
        "Technology": ([], (25, 69)),
        "Children's Books": ([], (6, 19)),
    },
    "Toys & Games": {
        "Board Games": (["Strategy Game", "Party Game", "Card Game", "Trivia Game"], (12, 79)),
        "Building Sets": (["Building Set", "Robot Kit", "Marble Run"], (15, 199)),
        "Puzzles": (["500-Piece Puzzle", "1000-Piece Puzzle", "3D Puzzle"], (9, 49)),
    },
    "Beauty & Health": {
        "Skincare": (["Moisturizer", "Face Serum", "Sunscreen", "Cleanser"], (8, 79)),
        "Hair Care": (["Shampoo", "Conditioner", "Hair Dryer", "Hair Oil"], (6, 149)),
        "Vitamins & Supplements": (["Multivitamin", "Vitamin D3", "Protein Powder", "Omega-3"],
                                   (9, 59)),
    },
    "Grocery": {
        "Coffee & Tea": (["Ground Coffee", "Whole Bean Coffee", "Green Tea", "Black Tea"], (6, 29)),
        "Snacks": (["Granola Bars", "Trail Mix", "Dark Chocolate", "Potato Chips"], (3, 15)),
    },
    "Office": {
        "Stationery": (["Notebook", "Gel Pens", "Sticky Notes", "Planner", "Highlighters"], (3, 35)),
        "Office Furniture": (["Standing Desk", "Office Chair", "Monitor Stand", "Filing Cabinet"],
                             (39, 799)),
    },
}

# section: (sku prefix, brands, modifiers, max quantity per order line)
SECTIONS = {
    "Electronics": ("ELE", ["Voltix", "Nimbus", "Arcwave", "Lumen", "Zentro", "Orbix"],
                    ["Pro", "Lite", "Max", "Air", "Plus", "Mini", "Ultra", "S", "X", "One"], 2),
    "Home & Kitchen": ("HOM", ["HearthCo", "Copperleaf", "Nestwell", "Brightside Home"],
                       ["Classic", "Essential", "Deluxe", "Compact", "Premium", "Everyday"], 2),
    "Sports & Outdoors": ("SPO", ["TrailPeak", "Ironform", "Velocity", "Summitline"],
                          ["Trail", "Pro", "Lightweight", "All-Weather", "Performance", "Compact"], 3),
    "Clothing": ("CLO", ["Northloom", "Urban Thread", "Cotton & Co", "Stride"],
                 ["Navy", "Black", "Heather Gray", "Olive", "White", "Burgundy", "Sand",
                  "Denim Blue"], 3),
    "Books": ("BOO", ["Harborlight Press", "Quill House", "Blue Fern Books",
                      "Pinecrest Publishing"], [], 2),
    "Toys & Games": ("TOY", ["Playforge", "Tiny Titans", "Brickwise"],
                     ["Classic", "Deluxe", "Junior", "Family", "Mega", "Travel"], 2),
    "Beauty & Health": ("BEA", ["Glowra", "PureRoots", "Verdant Lab"],
                        ["Hydrating", "Daily", "Gentle", "Revitalizing", "Night",
                         "Fragrance-Free"], 3),
    "Grocery": ("GRO", ["Roast Republic", "Good Grain", "Hillside Farms"],
                ["Organic", "Original", "Classic", "Sea Salt", "Honey", "Bold"], 6),
    "Office": ("OFF", ["Paperline", "Deskcraft", "Inkwell"],
               ["Classic", "Ergonomic", "Recycled", "Premium", "Compact"], 4),
}

BOOK_TITLES = {
    "Fiction": lambda: "The {} {}".format(
        rng.choice(["Silent", "Last", "Hidden", "Broken", "Golden", "Forgotten", "Midnight",
                    "Distant", "Burning", "Lost", "Crimson", "Quiet"]),
        rng.choice(["River", "Garden", "Kingdom", "Letter", "Harbor", "Promise", "Mountain",
                    "Archive", "Signal", "Orchard", "Lighthouse", "Winter"])),
    "Non-Fiction": lambda: rng.choice(["The Science of {}", "A Short Guide to {}",
                                       "{} Made Simple", "Rethinking {}", "The Art of {}"]).format(
        rng.choice(["Habits", "Money", "Sleep", "Focus", "Leadership", "Negotiation",
                    "Cooking", "Travel", "Running", "Memory"])),
    "Technology": lambda: "{} {}".format(
        rng.choice(["Python", "SQL", "Rust", "Docker", "Linux", "Kubernetes", "PostgreSQL",
                    "Git", "JavaScript", "Machine Learning", "Go", "Networking"]),
        rng.choice(["in Practice", "for Beginners", "Cookbook", "Deep Dive", "the Hard Way",
                    "Pocket Guide"])),
    "Children's Books": lambda: rng.choice(["The {} Who Loved Books", "Goodnight, {}",
                                            "{} Goes to School", "A Day with {}",
                                            "{} and the Big Storm"]).format(
        rng.choice(["Dragon", "Bunny", "Robot", "Little Bear", "Penguin", "Fox", "Owl"])),
}

SEASONALITY = {1: .55, 2: .55, 3: .65, 4: .65, 5: .7, 6: .7, 7: .7, 8: .75, 9: .7,
               10: .75, 11: .95, 12: 1.0}  # accept probability by month (holiday peak)
ITEMS_PER_ORDER_WEIGHTS = [18, 22, 20, 14, 10, 7, 5, 4]  # for 1..8 distinct products
DISCOUNTS = [Decimal("0.05"), Decimal("0.10"), Decimal("0.15"), Decimal("0.20")]


# ───────────────────────── entities ─────────────────────────

@dataclass
class Store:
    id: int
    name: str
    city: str
    state: str
    opened_at: date
    closed_at: date | None

    def is_open(self, d: date) -> bool:
        return self.opened_at <= d and (self.closed_at is None or d < self.closed_at)


@dataclass
class Employee:
    id: int
    first_name: str
    last_name: str
    email: str
    job_title: str
    department_id: int
    store_id: int | None
    manager_id: int | None
    salary: Decimal
    hire_date: date
    termination_date: date | None

    def active_on(self, d: date) -> bool:
        return self.hire_date <= d and (self.termination_date is None or d < self.termination_date)

    def row(self):
        return (self.id, self.first_name, self.last_name, self.email, self.job_title,
                self.department_id, self.store_id, self.manager_id, self.salary,
                self.hire_date, self.termination_date)


@dataclass
class Customer:
    id: int
    created_at: datetime
    weight: float
    address_ids: list[int] = field(default_factory=list)  # first one is the default


@dataclass
class Product:
    id: int
    price: Decimal
    created_at: datetime
    discontinued_at: datetime | None
    weight: float
    max_qty: int

    def available_at(self, t: datetime) -> bool:
        return self.created_at <= t and (self.discontinued_at is None or t < self.discontinued_at)


# ───────────────────────── builders ─────────────────────────

def build_hr():
    departments = [(i, name) for i, name in enumerate(DEPARTMENTS, start=1)]
    dept_id = {name: i for i, name in departments}
    stores = [Store(i, f"Kestrel Market {city}", city, state, opened, closed)
              for i, (city, state, opened, closed) in enumerate(STORES, start=1)]
    employees: list[Employee] = []

    def add(title, dept, pay, hire, manager=None, store=None, churn=0.0):
        hire = max(hire, manager.hire_date) if manager else hire
        work_end = min(store.closed_at, TODAY) if store and store.closed_at else TODAY
        term = None
        if rng.random() < churn and hire + timedelta(days=90) < work_end:
            term = rand_date(hire + timedelta(days=90), work_end)
        if store and store.closed_at and (term is None or term > store.closed_at):
            term = store.closed_at  # everybody left when the store closed
        first, last = fake.first_name(), fake.last_name()
        e = Employee(len(employees) + 1, first, last,
                     unique_email(f"{slug(first)}.{slug(last)}", "kestrelmarket.example"),
                     title, dept_id[dept], store.id if store else None,
                     manager.id if manager else None, salary(*pay), hire, term)
        employees.append(e)
        return e

    ceo = add("Chief Executive Officer", "Executive", (240_000, 260_000), COMPANY_START)
    heads = {d: add(f"Head of {d}", d, (120_000, 175_000),
                    rand_date(COMPANY_START, date(2019, 2, 28)), manager=ceo)
             for d in DEPARTMENTS if d != "Executive"}

    for s in stores:
        mgr = add("Store Manager", "Sales", (65_000, 85_000),
                  s.opened_at - timedelta(days=rng.randint(30, 60)), manager=heads["Sales"], store=s)
        last_hire = (s.closed_at or TODAY) - timedelta(days=30)
        for i in range(rng.randint(10, 16)):
            if i < 6:  # opening crew
                hire = rand_date(s.opened_at - timedelta(days=30), s.opened_at - timedelta(days=1))
            else:
                hire = rand_date(s.opened_at, last_hire)
            senior = rng.random() < 0.25
            add("Senior Sales Associate" if senior else "Sales Associate", "Sales",
                (42_000, 58_000) if senior else (32_000, 48_000), hire,
                manager=mgr, store=s, churn=0.3)

    for dept, (titles, headcount) in HQ_STAFF.items():
        boss = ceo if dept == "Executive" else heads[dept]
        for _ in range(headcount):
            title, lo, hi = rng.choice(titles)
            add(title, dept, (lo, hi), rand_date(date(2019, 3, 1), TODAY - timedelta(days=30)),
                manager=boss, churn=0.15)

    return departments, stores, employees


def build_catalog():
    categories, leaves = [], []  # leaves: (category_id, leaf name, section, nouns, price range)

    def walk(node, parent_id, section):
        for name, child in node.items():
            cid = len(categories) + 1
            categories.append((cid, name, parent_id))
            if isinstance(child, dict):
                walk(child, cid, section or name)
            else:
                leaves.append((cid, name, section, *child))

    walk(CATALOG, None, None)

    products, rows, used_names = [], [], set()
    leaf_weights = [1.5 if section == "Books" else 1.0 for _, _, section, _, _ in leaves]
    for pid in range(1, N_PRODUCTS + 1):
        cid, leaf, section, nouns, (lo, hi) = rng.choices(leaves, weights=leaf_weights)[0]
        code, brands, modifiers, max_qty = SECTIONS[section]
        for _ in range(20):
            brand = rng.choice(brands)
            if section == "Books":
                name = BOOK_TITLES[leaf]()
            elif section == "Electronics":
                name = f"{brand} {rng.choice(nouns)} {rng.choice(modifiers)} {rng.randint(2, 9)}"
            else:
                name = f"{brand} {rng.choice(modifiers)} {rng.choice(nouns)}"
            if (name, brand) not in used_names:
                break
        else:  # still a duplicate: make it a new edition / version
            n = 2
            while (f"{name} ({ordinal(n)} Edition)", brand) in used_names:
                n += 1
            name = f"{name} ({ordinal(n)} Edition)" if section == "Books" else f"{name} v{n}"
        used_names.add((name, brand))

        price = Decimal(rng.randint(lo + 1, hi + 1)) - CENT  # always .99
        cost = (price * Decimal(str(round(rng.uniform(0.40, 0.70), 3)))).quantize(CENT, ROUND_HALF_UP)
        if rng.random() < 0.7:
            created = rand_dt(datetime(2022, 1, 1, tzinfo=UTC), datetime(2022, 12, 31, tzinfo=UTC))
        else:
            created = rand_dt(datetime(2023, 1, 1, tzinfo=UTC), datetime(2026, 10, 1, tzinfo=UTC))
        discontinued = None
        if rng.random() < 0.08 and created + timedelta(days=180) < NOW - timedelta(days=1):
            discontinued = rand_dt(created + timedelta(days=180), NOW - timedelta(days=1))

        popularity = min(rng.paretovariate(1.2), 50)  # a few best-sellers, a long tail
        products.append(Product(pid, price, created, discontinued, popularity, max_qty))
        rows.append((pid, f"{code}-{pid:05d}", name, brand, cid, price, cost, created, discontinued))

    return categories, products, rows


def build_customers():
    customers, customer_rows, address_rows = [], [], []
    span_total = (NOW - ORDERS_START).total_seconds()
    for cid in range(1, N_CUSTOMERS + 1):
        first, last = fake.first_name(), fake.last_name()
        local = rng.choice([f"{first}.{last}", f"{first}{last}", f"{first[0]}{last}"])
        if rng.random() < 0.4:
            local += str(rng.randint(1, 99))
        email = unique_email(slug(local) if "." not in local else
                             ".".join(slug(p) for p in local.split(".")),
                             rng.choice(["example.com", "example.net", "example.org"]))
        phone = (f"({rng.randint(201, 989)}) {rng.randint(200, 999)}-{rng.randint(0, 9999):04d}"
                 if rng.random() < 0.85 else None)
        created = rand_dt(datetime(2022, 6, 1, tzinfo=UTC), datetime(2026, 10, 31, tzinfo=UTC))

        loyalty = 0.0 if rng.random() < 0.10 else min(rng.paretovariate(1.3), 20)
        active_share = (NOW - max(created, ORDERS_START)).total_seconds() / span_total
        c = Customer(cid, created, loyalty * active_share)

        n_addr = rng.choices([0, 1, 2, 3], weights=[5, 70, 20, 5])[0]
        home = rng.choice(CITIES)
        for i in range(n_addr):
            city, state = home if i == 0 else rng.choice(CITIES)
            aid = len(address_rows) + 1
            address_rows.append((aid, cid, fake.street_address(), city, state,
                                 fake.zipcode_in_state(state), i == 0))
            c.address_ids.append(aid)

        customers.append(c)
        customer_rows.append((cid, first, last, email, phone, created))
    return customers, customer_rows, address_rows


def build_orders(customers, products, stores, employees):
    sales_staff = {s.id: [e for e in employees if e.store_id == s.id] for s in stores}
    cust_cum = list(accumulate(c.weight for c in customers))
    prod_cum = list(accumulate(p.weight for p in products))
    latest_order = NOW - timedelta(hours=1)
    orders, items, payments = [], [], []

    for oid in range(1, N_ORDERS + 1):
        c = rng.choices(customers, cum_weights=cust_cum)[0]
        start = max(c.created_at, ORDERS_START)
        while True:
            t = rand_dt(start, latest_order)
            if rng.random() < SEASONALITY[t.month]:
                break
        d = t.date()

        store_id = employee_id = address_id = None
        if c.address_ids and rng.random() < 0.65:
            channel = "online"
            address_id = (c.address_ids[0] if len(c.address_ids) == 1 or rng.random() < 0.8
                          else rng.choice(c.address_ids[1:]))
        else:
            channel = "in_store"
            store = rng.choice([s for s in stores if s.is_open(d)])
            store_id = store.id
            employee_id = rng.choice([e for e in sales_staff[store.id] if e.active_on(d)]).id

        chosen: dict[int, Product] = {}
        wanted = rng.choices(range(1, 9), weights=ITEMS_PER_ORDER_WEIGHTS)[0]
        for _ in range(200):
            if len(chosen) == wanted:
                break
            p = rng.choices(products, cum_weights=prod_cum)[0]
            if p.id not in chosen and p.available_at(t):
                chosen[p.id] = p
        assert chosen, f"order {oid}: no product available at {t}"

        total = Decimal(0)
        for p in chosen.values():
            qty = 1 if rng.random() < 0.7 else rng.randint(2, p.max_qty)
            disc = Decimal(0) if rng.random() < 0.85 else rng.choice(DISCOUNTS)
            total += (p.price * qty * (1 - disc)).quantize(CENT, ROUND_HALF_UP)
            items.append((len(items) + 1, oid, p.id, qty, p.price, disc))

        shipped_at = delivered_at = None
        pays = []  # (method, amount, status, paid_at)
        if channel == "in_store":
            status, delivered_at = "delivered", t  # customer leaves with the products
            method = rng.choices(["cash", "credit_card", "debit_card", "gift_card"],
                                 weights=[25, 45, 25, 5])[0]
            if method != "cash" and rng.random() < 0.03:
                pays.append((method, total, "failed", t))
            pays.append((method, total, "completed", t + timedelta(seconds=rng.randint(20, 90))))
        else:
            method = rng.choices(["credit_card", "debit_card", "paypal", "gift_card"],
                                 weights=[55, 20, 20, 5])[0]
            paid_at = t + timedelta(minutes=rng.randint(1, 30))
            r = rng.random()
            if r < 0.02:
                status = "cancelled"  # cancelled before paying
            elif r < 0.04:
                status = "cancelled"  # paid, then cancelled and refunded
                pays.append((method, total, "refunded", paid_at))
            elif t > NOW - timedelta(days=2) and rng.random() < 0.3:
                status = "pending"  # still waiting for payment
            else:
                if rng.random() < 0.06:
                    pays.append((method, total, "failed", t + timedelta(seconds=rng.randint(10, 50))))
                pays.append((method, total, "completed", paid_at))
                ship = trunc(paid_at + timedelta(hours=rng.uniform(12, 72)))
                deliver = trunc(ship + timedelta(hours=rng.uniform(24, 144)))
                if ship > NOW:
                    status = "paid"
                elif deliver > NOW:
                    status, shipped_at = "shipped", ship
                else:
                    status, shipped_at, delivered_at = "delivered", ship, deliver

        orders.append((oid, c.id, channel, store_id, employee_id, address_id, status, t,
                       shipped_at, delivered_at))
        for method, amount, pstatus, at in pays:
            payments.append((len(payments) + 1, oid, method, amount, pstatus, at))

    return orders, items, payments


# ───────────────────────── load & verify ─────────────────────────

TABLES = {
    "departments": ["id", "name"],
    "stores": ["id", "name", "city", "state", "opened_at", "closed_at"],
    "employees": ["id", "first_name", "last_name", "email", "job_title", "department_id",
                  "store_id", "manager_id", "salary", "hire_date", "termination_date"],
    "categories": ["id", "name", "parent_id"],
    "products": ["id", "sku", "name", "brand", "category_id", "price", "cost", "created_at",
                 "discontinued_at"],
    "customers": ["id", "first_name", "last_name", "email", "phone", "created_at"],
    "addresses": ["id", "customer_id", "street", "city", "state", "zip_code", "is_default"],
    "orders": ["id", "customer_id", "channel", "store_id", "employee_id", "shipping_address_id",
               "status", "ordered_at", "shipped_at", "delivered_at"],
    "order_items": ["id", "order_id", "product_id", "quantity", "unit_price", "discount"],
    "payments": ["id", "order_id", "method", "amount", "status", "paid_at"],
}

ORDER_TOTALS = """
    SELECT order_id, sum(round(quantity * unit_price * (1 - discount), 2)) AS total
    FROM order_items GROUP BY order_id
"""

# Each query counts rows that break a business rule. All must return 0.
CHECKS = {
    "order placed before the customer signed up":
        "SELECT count(*) FROM orders o JOIN customers c ON c.id = o.customer_id "
        "WHERE o.ordered_at < c.created_at",
    "in-store order while the store was closed":
        "SELECT count(*) FROM orders o JOIN stores s ON s.id = o.store_id "
        "WHERE o.ordered_at::date < s.opened_at OR o.ordered_at::date >= s.closed_at",
    "salesperson not working at that store that day":
        "SELECT count(*) FROM orders o JOIN employees e ON e.id = o.employee_id "
        "WHERE e.store_id IS DISTINCT FROM o.store_id OR o.ordered_at::date < e.hire_date "
        "OR o.ordered_at::date >= e.termination_date",
    "product sold outside its availability window":
        "SELECT count(*) FROM order_items oi JOIN orders o ON o.id = oi.order_id "
        "JOIN products p ON p.id = oi.product_id "
        "WHERE o.ordered_at < p.created_at OR o.ordered_at >= p.discontinued_at",
    "unit_price different from product price":
        "SELECT count(*) FROM order_items oi JOIN products p ON p.id = oi.product_id "
        "WHERE oi.unit_price <> p.price",
    "shipped to another customer's address":
        "SELECT count(*) FROM orders o JOIN addresses a ON a.id = o.shipping_address_id "
        "WHERE a.customer_id <> o.customer_id",
    "order without items":
        "SELECT count(*) FROM orders o WHERE NOT EXISTS "
        "(SELECT 1 FROM order_items oi WHERE oi.order_id = o.id)",
    "completed payment different from order total":
        f"SELECT count(*) FROM ({ORDER_TOTALS}) t JOIN payments p USING (order_id) "
        "WHERE p.status = 'completed' AND p.amount <> t.total",
    "paid/shipped/delivered order without exactly one completed payment":
        "SELECT count(*) FROM orders o WHERE o.status IN ('paid', 'shipped', 'delivered') "
        "AND (SELECT count(*) FROM payments p WHERE p.order_id = o.id "
        "AND p.status = 'completed') <> 1",
    "pending/cancelled order with a completed payment":
        "SELECT count(*) FROM orders o JOIN payments p ON p.order_id = o.id "
        "WHERE o.status IN ('pending', 'cancelled') AND p.status = 'completed'",
    "status inconsistent with timestamps":
        "SELECT count(*) FROM orders WHERE "
        "(status = 'delivered' AND delivered_at IS NULL) "
        "OR (status = 'shipped' AND (shipped_at IS NULL OR delivered_at IS NOT NULL)) "
        "OR (status IN ('pending', 'paid', 'cancelled') "
        "    AND (shipped_at IS NOT NULL OR delivered_at IS NOT NULL))",
    "payment before the order":
        "SELECT count(*) FROM payments p JOIN orders o ON o.id = p.order_id "
        "WHERE p.paid_at < o.ordered_at",
    "employee hired before their manager":
        "SELECT count(*) FROM employees e JOIN employees m ON m.id = e.manager_id "
        "WHERE e.hire_date < m.hire_date",
    "active employee whose manager left":
        "SELECT count(*) FROM employees e JOIN employees m ON m.id = e.manager_id "
        "WHERE e.termination_date IS NULL AND m.termination_date IS NOT NULL",
    "still employed at a closed store":
        "SELECT count(*) FROM employees e JOIN stores s ON s.id = e.store_id "
        "WHERE s.closed_at IS NOT NULL "
        "AND (e.termination_date IS NULL OR e.termination_date > s.closed_at)",
    "customer with addresses but not exactly one default":
        "SELECT count(*) FROM (SELECT customer_id FROM addresses GROUP BY customer_id "
        "HAVING count(*) FILTER (WHERE is_default) <> 1) x",
    "product in a non-leaf category":
        "SELECT count(*) FROM products p WHERE EXISTS "
        "(SELECT 1 FROM categories c WHERE c.parent_id = p.category_id)",
    "event in the future":
        f"SELECT count(*) FROM orders WHERE greatest(ordered_at, shipped_at, delivered_at) "
        f"> '{NOW.isoformat()}'",
}


def load(conn: psycopg.Connection, data: dict[str, list[tuple]]) -> None:
    with conn.cursor() as cur:
        cur.execute(Path(__file__).with_name("schema.sql").read_text())
        for table, columns in TABLES.items():
            with cur.copy(f"COPY {table} ({', '.join(columns)}) FROM STDIN") as copy:
                for row in data[table]:
                    copy.write_row(row)
            cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                        f"(SELECT max(id) FROM {table}))")
    conn.commit()
    conn.autocommit = True
    conn.execute("VACUUM ANALYZE")
    conn.execute("SELECT pg_stat_statements_reset()")


def verify(conn: psycopg.Connection) -> bool:
    ok = True
    for name, sql in CHECKS.items():
        bad = conn.execute(sql).fetchone()[0]
        ok &= bad == 0
        print(f"  {'OK  ' if bad == 0 else 'FAIL'} {name}" + (f"  ({bad} rows)" if bad else ""))
    return ok


def main() -> None:
    t0 = time.perf_counter()
    departments, stores, employees = build_hr()
    categories, products, product_rows = build_catalog()
    customers, customer_rows, address_rows = build_customers()
    orders, items, payments = build_orders(customers, products, stores, employees)
    data = {
        "departments": departments,
        "stores": [(s.id, s.name, s.city, s.state, s.opened_at, s.closed_at) for s in stores],
        "employees": [e.row() for e in employees],
        "categories": categories,
        "products": product_rows,
        "customers": customer_rows,
        "addresses": address_rows,
        "orders": orders,
        "order_items": items,
        "payments": payments,
    }
    print(f"Generated data in {time.perf_counter() - t0:.1f}s")

    with psycopg.connect(DSN, options="-c timezone=UTC") as conn:
        load(conn, data)
        print(f"Loaded into PostgreSQL in {time.perf_counter() - t0:.1f}s total\n")
        for table in TABLES:
            print(f"  {table:<12} {len(data[table]):>8,} rows")
        print(f"  {'TOTAL':<12} {sum(len(v) for v in data.values()):>8,} rows\n")
        print("Coherence checks:")
        if not verify(conn):
            raise SystemExit("Some coherence checks failed.")
    print("\nDone. Connect with: psql postgresql://lab:lab@localhost:5433/shop")


if __name__ == "__main__":
    main()
