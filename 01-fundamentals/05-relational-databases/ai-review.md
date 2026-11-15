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

## Prompt que funcionó

```text
<pendiente>
```

## Errores que encontré en el lab

- [ ] …
