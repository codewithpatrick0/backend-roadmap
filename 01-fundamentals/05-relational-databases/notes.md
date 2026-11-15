# Bases de datos relacionales, migraciones y el problema N+1

> Issue: #5 · Prioridad: ★★★ · Lab: [`labs/sql-lab`](../../labs/sql-lab/) (Kestrel Market)

## Qué es (en una frase)

## Qué problema resuelve

## Conceptos clave

- **Tabla, fila, columna, clave primaria (PK)**:
- **Clave foránea (FK)** y por qué PostgreSQL **no** la indexa sola:
- **JOINs** (`INNER`, `LEFT`, self-join):
- **Agregaciones** (`GROUP BY`, `HAVING`) y el fan-out:
- **Funciones de ventana** (`RANK`, `LAG`, `SUM() OVER`):
- **CTE recursivas**:
- **`EXPLAIN ANALYZE`** e índices:
- **Migraciones** (Alembic):
- **Problema N+1** y `joinedload` / `selectinload`:

## Avance en el lab

Ejercicios del [README del lab](../../labs/sql-lab/README.md#ejercicios-sugeridos-sin-soluciones):

- [x] 1. Calentamiento (1–3)
- [x] 2. JOINs (4–7)
- [ ] 3. Agregaciones (8–11)
- [ ] 4. Funciones de ventana (12–15)
- [ ] 5. CTE recursivas (16–18)
- [ ] 6. Trampas clásicas (19–22)
- [ ] 7. Rendimiento (23–25)
- [ ] 8. ORM y N+1 (26–31)
- [ ] Migraciones con Alembic (pendiente de agregar al lab)

## Preguntas de entrevista

- ¿Qué es el problema N+1 y cómo lo detectas?
- ¿Diferencia entre `LEFT JOIN … IS NULL` y `NOT EXISTS`? ¿Por qué `NOT IN` falla con `NULL`?
- ¿Cuándo crearías un índice y cuándo no?

## Lo que aprendí en el lab

## Recursos

- [roadmap.sh/backend](https://roadmap.sh/backend)
- [PostgreSQL docs](https://www.postgresql.org/docs/current/)
- [SQLAlchemy 2.0 — Relationship loading](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html)
