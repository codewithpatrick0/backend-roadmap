# Bases de datos relacionales, migraciones y el problema N+1

> Issue: #5 · Prioridad: ★★★ · Lab: [`labs/sql-lab`](../../labs/sql-lab/) (Kestrel Market)

## Qué es (en una frase)

Una base de datos que guarda la información en tablas relacionadas entre sí por claves, y que se consulta con SQL.

## Qué problema resuelve

Guardar datos sin repetirlos, con reglas que la propia base garantiza (claves, restricciones, transacciones), y poder responder cualquier pregunta del negocio cruzando tablas.

## Conceptos clave

- **Tabla, fila, columna, clave primaria (PK)**: cada fila es una cosa (un pedido, un cliente) y la PK la identifica de forma única. Para agrupar o contar, uso la PK, no el nombre: dos personas pueden llamarse igual.
- **Clave foránea (FK)** y por qué PostgreSQL **no** la indexa sola: la FK solo garantiza que el valor exista en la otra tabla. El índice lo tengo que crear yo, si filtro o uno por esa columna a menudo.
- **JOINs** (`INNER`, `LEFT`, self-join): `INNER` deja solo lo que coincide; `LEFT` deja todo lo de la izquierda. En un `LEFT JOIN`, el filtro de la tabla derecha va en el `ON`, no en el `WHERE`. Self-join = la misma tabla dos veces con roles distintos (empleado y jefe).
- **Agregaciones** (`GROUP BY`, `HAVING`) y el fan-out: antes de mirar un `SUM` o un `COUNT`, me pregunto **¿qué es cada fila después de mis JOINs?** Dos JOINs 1:N multiplican las filas entre sí. Solución: agregar cada tabla por separado (CTE) y después unir.
- **Funciones de ventana** (`RANK`, `LAG`, `SUM() OVER`): calculan sobre un grupo de filas sin juntarlas. "Dentro de cada X" = `PARTITION BY X`; sin eso la consulta responde otra pregunta.
- **CTE recursivas**: un ancla (el punto de partida) + un paso que se une con la propia CTE. Sirve para árboles de cualquier profundidad (categorías, organigramas). El `parent_id` va en el alias nuevo, si no, sube en vez de bajar.
- **`EXPLAIN ANALYZE`** e índices: `Seq Scan` en una tabla grande = probablemente falta un índice. Un índice `(a, b)` no sirve para buscar solo por `b`. Que el plan diga `Index Scan` no prueba que ayude: miro el tiempo real.
- **Migraciones** (Alembic): cambios del esquema versionados en código, para que todos los entornos tengan la misma estructura. Ya lo conozco; lo refuerzo sobre la marcha.
- **Problema N+1** y `joinedload` / `selectinload`: 1 consulta para la lista + 1 por cada elemento al tocar una relación dentro de un bucle. `joinedload` para relaciones a uno, `selectinload` para colecciones, `raiseload` para que el N+1 explote en vez de esconderse.

## Avance en el lab

Ejercicios del [README del lab](../../labs/sql-lab/README.md#ejercicios-sugeridos-sin-soluciones):

- [x] 1. Calentamiento (1–3)
- [x] 2. JOINs (4–7)
- [x] 3. Agregaciones (8–11)
- [x] 4. Funciones de ventana (12–15)
- [x] 5. CTE recursivas (16–18)
- [x] 6. Trampas clásicas (19–22)
- [x] 7. Rendimiento (23–25)
- [x] 8. ORM y N+1 (26–31)
- [ ] Migraciones con Alembic: ya lo conozco, lo refuerzo sobre la marcha

## Preguntas de entrevista

- ¿Qué es el problema N+1 y cómo lo detectas?
- ¿Diferencia entre `LEFT JOIN … IS NULL` y `NOT EXISTS`? ¿Por qué `NOT IN` falla con `NULL`?
- ¿Cuándo crearías un índice y cuándo no?

## Lo que aprendí en el lab

- **La granularidad es mi punto débil y mi mejor herramienta.** Fallé los ejercicios 19 y 21 por no preguntarme qué era cada fila después del JOIN. En el repaso ya lo veía.
- **Una consulta puede correr sin error y estar mal**: `NOT IN` con `NULL` devuelve 0 filas, una ventana sin `PARTITION BY` compara contra todo, y `::date` cambia según la zona horaria de la sesión.
- **Validación cruzada**: si dos caminos distintos dan el mismo número al centavo (ventas por `order_items` y por `payments`), la consulta está bien.
- **Escribir para la regla del negocio, no para los datos de hoy**: un arreglo que funciona "porque hoy hay un solo pago por pedido" se rompe cuando aparecen las cuotas.
- **Antes de arreglar un JOIN, preguntar si hace falta**: muchos bugs desaparecen quitando la tabla que sobra.
- **Bug vs mejora**: si el resultado cambia al arreglarlo, es un bug.
- **Que la base calcule**: sumar 44 mil pedidos en Python tardó 2.5 s; con `func.sum` + `group_by`, 0.12 s.
- Mis errores y lo que la IA suele hacer mal están en [`ai-review.md`](ai-review.md) (24 trampas).

## Recursos

- [roadmap.sh/backend](https://roadmap.sh/backend)
- [PostgreSQL docs](https://www.postgresql.org/docs/current/)
- [SQLAlchemy 2.0 — Relationship loading](https://docs.sqlalchemy.org/en/20/orm/queryguide/relationships.html)
