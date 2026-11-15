# SQL Lab — Kestrel Market

Base de datos ficticia de **Kestrel Market**, una cadena minorista de EE.UU. que vende de todo
(electrónica, hogar, ropa, libros, comida…) por **internet** y en **12 tiendas físicas**.
Sirve para practicar SQL y luego SQLAlchemy 2.0 (joins, N+1, índices, etc.).

Los datos son reproducibles (semilla fija) y el "hoy" del dataset está congelado en
**2026-11-13**.

## Puesta en marcha

```bash
cd ~/Desktop/ROADMAP/labs/sql-lab
docker compose up -d --wait       # levanta PostgreSQL 17 en localhost:5433
uv sync                           # instala SQLAlchemy, psycopg y Faker
uv run python generate.py         # crea el esquema, carga ~256k filas y valida coherencia
```

Conectarte:

```bash
psql postgresql://lab:lab@localhost:5433/shop
```

Resetear todo (por ejemplo, después de crear índices o romper datos): vuelve a ejecutar
`uv run python generate.py`. Borrar el contenedor y su volumen: `docker compose down -v`.

> El puerto es **5433** porque tu PostgreSQL local ya usa el 5432. El contenedor solo escucha en
> `127.0.0.1` porque la contraseña (`lab`) es débil a propósito.

## Modelo de datos

```
departments ─┐
             ├─< employees >─┐ manager_id → employees (self-join, jerarquía)
stores ──────┘       │       │
   │                 │ (vendedor, solo en tienda)
   └──────────────< orders >──────────── customers ──< addresses
                    │   │   └── shipping_address_id → addresses (solo online)
                    │   └────< payments
                    └────< order_items >── products >── categories ──┐
                                                            parent_id ┘ (árbol)
```

| Tabla | Filas | Notas |
|---|---:|---|
| `departments` | 8 | Executive, Sales, Customer Service, IT… |
| `stores` | 12 | Portland **cerró** el 2025-06-30 |
| `employees` | 244 | `store_id` NULL = oficina central; `manager_id` NULL = CEO |
| `categories` | 44 | Árbol de **profundidad mixta**: `Electronics > Laptops` y `Electronics > Audio > Headphones` |
| `products` | 1,500 | Solo en categorías hoja; algunos descontinuados |
| `customers` | 5,000 | ~15% sin teléfono, ~5% sin dirección, ~17% nunca compró |
| `addresses` | 6,254 | Exactamente una `is_default` por cliente que tenga direcciones |
| `orders` | 45,000 | Ene-2023 → nov-2026, con pico en noviembre/diciembre |
| `order_items` | 151,455 | |
| `payments` | 46,434 | Algunos pedidos tienen un intento `failed` antes del `completed` |

### Reglas de negocio (garantizadas por `generate.py`, que las verifica al final)

- **Canal**: `online` → tiene `shipping_address_id`, sin tienda ni vendedor. `in_store` → tiene
  `store_id` y `employee_id`, sin dirección, y se entrega al instante (`delivered`).
- **Total del pedido**: no se guarda. Es `sum(round(quantity * unit_price * (1 - discount), 2))`
  de sus `order_items`, y coincide exacto con el pago `completed`.
- **Estados** (online): `pending` (sin pagar, solo pedidos de los últimos 2 días) → `paid` →
  `shipped` (`shipped_at`) → `delivered` (`delivered_at`). `cancelled`: sin pago, o con un pago
  `refunded`.
- Un pedido solo incluye productos disponibles en esa fecha (`created_at` ≤ fecha <
  `discontinued_at`), y en tienda lo atiende un empleado de **esa** tienda que trabajaba ese día.
- `unit_price` = `products.price` (los precios nunca cambiaron).
- `termination_date` es el primer día que la persona ya no trabaja (igual que `closed_at`).
- Todas las fechas/horas están en **UTC**.

### Índices

Solo existen las claves primarias, los `UNIQUE` (`email`, `sku`, `(order_id, product_id)`…) y un
índice parcial para la dirección por defecto. **Las columnas de foreign keys no tienen índice a
propósito**: PostgreSQL no las indexa automáticamente, y descubrirlo es parte del laboratorio.
`pg_stat_statements` está activado para ver qué consultas consumen más tiempo.

## Python / SQLAlchemy

- `models.py` — modelos mapeados a las tablas. Todas las relaciones usan el lazy loading por
  defecto (`lazy="select"`), así que el N+1 aparece solo.
- `db.py` — `engine`, `Session` y `count_queries()`, que cuenta cuántas consultas se envían:

```python
from db import Session, count_queries

with Session() as session, count_queries("mi experimento"):
    ...  # tu código ORM aquí
# imprime: [mi experimento] 101 queries in 340.2 ms
```

- `SQL_ECHO=1 uv run python script.py` imprime cada SQL que genera el ORM.
- `uv run python smoke_test.py` comprueba que todo está conectado.

## Ejercicios sugeridos (sin soluciones)

### 1. Calentamiento
1. Los 10 productos más caros con su categoría.
2. Clientes registrados en 2024 que no tienen teléfono.
3. ¿Cuántos empleados activos hay hoy en cada tienda?

### 2. JOINs
4. Clientes que **nunca** han comprado (hazlo con `LEFT JOIN` y luego con `NOT EXISTS`).
5. Productos que nunca se vendieron.
6. Cada empleado con el nombre de su jefe (self-join). ¿Por qué el CEO desaparece con `INNER JOIN`?
7. Pedidos online cuya dirección de envío está en un estado distinto al de la dirección por
   defecto del cliente.

### 3. Agregaciones
8. Ventas totales por mes (con el total calculado desde `order_items`).
9. Ventas por **sección** (Electronics, Books…). Cuidado: hay productos a 2 y a 3 niveles de
   profundidad.
10. Ticket promedio por canal y por método de pago.
11. Las 5 tiendas con más ventas en 2025. ¿Aparece Portland? ¿Debería?

### 4. Funciones de ventana
12. Ranking de vendedores dentro de cada tienda (`RANK() OVER (PARTITION BY …)`).
13. Total acumulado de ventas día a día en noviembre de 2025.
14. Días entre pedidos consecutivos de cada cliente (`LAG`).
15. Margen (`price - cost`) por producto y su percentil dentro de su categoría.

### 5. CTE recursivas
16. Ruta completa de cada categoría: `Electronics > Accessories > Chargers & Cables`.
17. Organigrama desde el CEO con el nivel de cada empleado.
18. Todos los empleados que dependen (directa o indirectamente) del Head of Sales.

### 6. Trampas clásicas
19. **Fan-out**: calcula total vendido y total pagado por pedido en **una sola** consulta con
    `JOIN order_items` y `JOIN payments`. Compara con los números reales. ¿Qué pasó?
20. **NOT IN con NULL**: empleados que nunca hicieron una venta usando
    `WHERE id NOT IN (SELECT employee_id FROM orders)`. ¿Por qué no devuelve nada?
21. `COUNT(*)` vs `COUNT(phone)` vs `COUNT(DISTINCT customer_id)`.
22. Pedidos "de ayer": ¿qué cambia si haces `SET timezone = 'America/Lima'`?

### 7. Rendimiento
23. `EXPLAIN ANALYZE` de "todos los pedidos del cliente 42". Crea el índice que falta y compara.
24. Lo mismo para `order_items` por `product_id`. ¿Qué otros FK necesitan índice?
25. Revisa `pg_stat_statements` después de correr tus scripts ORM: ¿cuál es la consulta más
    repetida?

### 8. ORM y N+1 (SQLAlchemy)
26. Imprime los últimos 100 pedidos con el nombre del cliente. Mide con `count_queries`.
    Arréglalo con `joinedload` y luego con `selectinload`: ¿cuántas consultas hace cada uno?
27. N+1 anidado: pedido → items → producto → categoría. Llévalo al menor número de consultas.
28. `joinedload` sobre una colección (`Order.items`) + `LIMIT`: ¿qué hace SQLAlchemy para que el
    límite no se rompa?
29. Usa `lazy="raise"` (o `raiseload("*")`) para que el N+1 explote en vez de pasar desapercibido.
30. Filtra pedidos con items de la sección Books **y** carga solo esos items
    (`contains_eager`).
31. Reescribe el ejercicio 8 con el ORM sin traer filas a Python (`func.sum`, `group_by`).
