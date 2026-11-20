# Más bases de datos: transacciones, ACID, ORMs, normalización, profiling

> Issue: #19 · Prioridad: ★★★ · Lab: compartido con [01·05](../../01-fundamentals/05-relational-databases/) (Kestrel Market)

## Qué es (en una frase)

Lo que hace falta para usar una base relacional en una aplicación real: que los datos no queden a medias, que el esquema no repita información, que el ORM no dispare cientos de consultas y saber medir qué es lento.

## Conceptos clave

- **ORMs** ✅ *(practicado: ejercicios 26–31)*: el ORM traduce objetos a SQL, pero por defecto carga las relaciones "cuando las tocas" (*lazy*), y eso produce el N+1. `joinedload` para relaciones a uno, `selectinload` para colecciones, `contains_eager` para cargar solo lo filtrado, `raiseload` para que el N+1 falle en los tests. Si necesito un resumen, `func.sum` + `group_by`: que la base calcule.
- **Profiling** ✅ *(practicado: ejercicios 23–25)*: `EXPLAIN ANALYZE` muestra el plan y el tiempo real de **una** consulta; `pg_stat_statements` muestra qué consultas se repiten o pesan más en **toda** la aplicación. La huella de un N+1: la misma consulta con muchos `calls` y ~1 fila cada una.
- **Transacciones** 🔄 *(sobre la marcha)*: varias escrituras que se aplican **todas o ninguna** (`BEGIN … COMMIT`, o `ROLLBACK` si algo falla). Ejemplo: crear el pedido, sus líneas y el pago. En SQLAlchemy: `with session.begin():`.
- **ACID** 🔄 *(sobre la marcha)*:
  - **Atomicidad**: todo o nada.
  - **Consistencia**: las restricciones (FK, `CHECK`, `UNIQUE`) se cumplen antes y después.
  - **Aislamiento**: dos transacciones a la vez no se pisan (niveles: `READ COMMITTED`, `REPEATABLE READ`, `SERIALIZABLE`).
  - **Durabilidad**: lo confirmado sobrevive a un corte de luz.
- **Normalización** 🔄 *(sobre la marcha)*: no repetir datos. Cada dato vive en un solo lugar y se referencia con FKs (por ejemplo, el nombre del cliente está en `customers`, no copiado en cada pedido). A veces se *desnormaliza* a propósito por rendimiento: `order_items.unit_price` guarda el precio del momento de la venta, porque `products.price` cambia.

## Preguntas de entrevista

- ¿Qué es una transacción y qué significa cada letra de ACID?
- ¿Qué es el problema N+1, cómo lo detectas y cómo lo resuelves con un ORM?
- ¿Cómo averiguas por qué una consulta es lenta?
- ¿Cuándo tiene sentido desnormalizar?

## Pendiente sobre la marcha

- [ ] Probar una transacción que falla a la mitad y comprobar el `ROLLBACK`.
- [ ] Ver un caso de aislamiento: dos sesiones modificando la misma fila.
- [ ] Migraciones con Alembic en un proyecto real.
