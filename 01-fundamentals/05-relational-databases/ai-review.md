# Revisar código de IA: bases de datos relacionales

Errores típicos que la IA comete en este tema y cómo detectarlos.

| # | Qué busco | Por qué es un problema | Cómo lo verifico |
|---|---|---|---|
| 1 | Relaciones ORM recorridas en un loop sin `selectinload`/`joinedload` | **N+1**: 1 consulta + 1 por cada fila | `count_queries()` o `SQL_ECHO=1` |
| 2 | FKs usadas en `WHERE`/`JOIN` sin índice | PostgreSQL no las indexa solo: *seq scan* en tablas grandes | `EXPLAIN ANALYZE` |
| 3 | SQL armado con f-strings o `+` | **SQL injection** 🔒 | Buscar `f"SELECT`, `.format(` → usar parámetros |
| 4 | `NOT IN (subquery)` donde la subquery puede devolver `NULL` | Devuelve 0 filas sin error | Cambiar a `NOT EXISTS` |
| 5 | Dos `JOIN` a tablas hijas + `SUM` en la misma consulta | **Fan-out**: los totales salen multiplicados | Comparar con cada suma por separado |
| 6 | `timestamp` sin zona horaria o `datetime.now()` sin `tz` | Fechas ambiguas, errores de "ayer" | Usar `timestamptz` y UTC |
| 7 | Varias escrituras relacionadas sin transacción | Datos a medias si algo falla | Ver que estén en el mismo `session.begin()` |
| 8 | `SELECT *` o traer todas las filas a Python para sumar | Lento y gasta memoria | Pedir `func.sum` + `group_by` en la BD |
| 9 | `joinedload` sobre colecciones + `LIMIT` | Filas duplicadas o límite roto | Preferir `selectinload` para colecciones |
| 10 | Columnas sin alias dentro de una subconsulta | Si la columna no existe en la tabla interna, PostgreSQL usa en silencio la de la consulta externa (`WHERE id IN (SELECT id …)` → devuelve todo) | Exigir alias (`o.customer_id`); así falla con "column does not exist" |
| 11 | `COUNT(parent.id)` después de un JOIN 1:N | Cuenta líneas, no pedidos (919 → 3,162) | Preguntar "¿qué es cada fila?" (granularidad); usar `COUNT(DISTINCT …)` |
| 12 | `ROUND(SUM(x))` en vez de `SUM(ROUND(x))` | El total no cuadra con lo cobrado ($8.19 de diferencia) | Redondear donde se cobra; validar contra `payments` |
| 13 | Filtros de estado en lista negra (`<> 'failed'`) | Estados olvidados o nuevos se cuelan (578 `refunded`) | Preferir lista blanca: `= 'completed'` / `IN (…)` |
| 14 | `AVG` sobre líneas cuando se pide el promedio por pedido | Mide otra cosa ($183 vs $816) | Agregar en dos niveles: total por pedido, después `AVG` |
| 15 | Filtrar por una fecha (`paid_at`) y agrupar por otra (`ordered_at`) | Los bordes del rango quedan mal: aparecen días fuera del mes y se pierden otros | Usar la misma columna en `WHERE` y `GROUP BY` |
| 16 | `GROUP BY` por nombre o email en vez de la PK | Dos personas con el mismo nombre se suman como una | Agrupar por `id` (y agregar las columnas que se muestran) |
| 17 | Restar fechas sin decidir la unidad (`date - date` vs `timestamp - timestamp`) | Días de calendario ≠ tiempo real: 504 vs 503 días 15 h; con `::date`, 1,332 compras de menos de 1 día se ven como 0 o 1 | Preguntar qué pide el negocio; probar con un caso conocido |
| 18 | Ventana sin `PARTITION BY` cuando se pide "dentro de cada X" | Compara contra toda la tabla: el mejor snack sale en el percentil 0.21 en vez de 1.00 | Cada grupo debe tener su propio 0 y su propio 1 (`min`/`max` por grupo) |
| 19 | CTE recursiva con el JOIN invertido (`o.manager_id = e.id`) | Sube por el árbol en vez de bajar: el organigrama devuelve 1 fila en vez de 244, sin error | El `parent_id`/`manager_id` va en el alias nuevo; un árbol completo devuelve tantas filas como la tabla |
| 20 | Arreglo que funciona "porque hoy los datos son así" (1 solo pago `completed` por pedido) | Ninguna restricción lo garantiza: con pagos en cuotas vuelve el fan-out | Preguntar "¿qué lo garantiza?"; si no hay constraint, agregar antes de unir |
| 21 | `COUNT(*)` o `COUNT(col)` de la tabla padre después de un `LEFT JOIN` 1:N | Cuenta pedidos, no clientes: 45,858 "clientes" en vez de 5,000 | Revisar la granularidad; contar sin JOIN o con `COUNT(DISTINCT id)` |
| 22 | `ordered_at::date = …` para "pedidos de ayer" | Depende de la zona horaria de la sesión: 69 (UTC), 63 (Lima), 66 (Tokio) | Rango semiabierto con la zona en el literal: `>= timestamptz '… America/Lima'` |
| 23 | `SUM(DISTINCT monto)` para "arreglar" un fan-out | Elimina valores iguales, no filas repetidas: 18.99 + 18.99 → 18.99; 568 pedidos mal ($24,141.28) | `DISTINCT` solo sobre claves únicas; mejor quitar el JOIN que sobra o agregar antes de unir |
| 24 | JOINs que no aportan columnas a la respuesta | Cada JOIN 1:N innecesario es un fan-out esperando a ocurrir | Por cada tabla del `FROM`, preguntar "¿qué columna uso de aquí?" |

## Prompt que funcionó

```text
Write a PostgreSQL query for: <business question>.
Before the query, state the grain: what does each row represent after every JOIN?
Rules: alias every column; aggregate child tables before joining them; use NOT EXISTS
instead of NOT IN; use status allowlists (= 'completed'); half-open date ranges with an
explicit time zone. After the query, give one known case I can use to check the result.
```

## Errores que encontré en el lab

Modo rápido (Claude escribía la consulta con un bug escondido y yo lo buscaba):

- [x] Ventana sin `PARTITION BY`: la vi, pero la llamé "mejora" (ej. 15) → trampa 18.
- [x] JOIN recursivo invertido: el organigrama devolvía 1 fila (ej. 17) → trampa 19.
- [x] Fan-out con dos tablas hijas: vi el `failed`, no la multiplicación (ej. 19) → trampas 5 y 20.
- [x] `NOT IN` con `NULL` devolvía 0 filas (ej. 20) → trampa 4.
- [x] `COUNT` de la tabla padre después de un `LEFT JOIN` (ej. 21) → trampa 21.
- [x] `::date` dependía de la zona horaria de la sesión (ej. 22) → trampa 22.
- [x] `SUM(DISTINCT)` como falso arreglo del fan-out (repaso 4) → trampa 23.
- [x] "Ya usa `Index Scan`", pero sobre un índice compuesto que no servía (ej. 24).
- [x] N+1: 366 consultas para 100 pedidos (ej. 27), y sumas en Python en vez de en la base (ej. 31) → trampas 1 y 8.
