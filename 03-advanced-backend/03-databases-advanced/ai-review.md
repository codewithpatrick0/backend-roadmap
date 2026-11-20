# Revisar código de IA: más bases de datos

Las trampas de ORM y rendimiento están en el [`ai-review.md` de 01·05](../../01-fundamentals/05-relational-databases/ai-review.md): 1 (N+1), 2 (FK sin índice), 7 (escrituras sin transacción), 8 (sumar en Python), 9 (`joinedload` + `LIMIT`), y de la 20 a la 24.

| # | Qué busco | Por qué es un problema | Cómo lo verifico |
|---|---|---|---|
| 1 | `session.commit()` dentro de un bucle | Cada vuelta es una transacción: si falla a la mitad, quedan datos a medias | Un solo `with session.begin():` alrededor de todo |
| 2 | Leer un valor, calcular en Python y escribirlo (`stock = stock - 1`) | Dos peticiones a la vez se pisan (*lost update*) | `UPDATE … SET stock = stock - 1` en la base, o `SELECT … FOR UPDATE` |
| 3 | Copiar datos de otra tabla "por comodidad" (nombre del cliente en el pedido) | Se desincronizan cuando el original cambia | Preguntar si es una foto a propósito (precio de venta) o una copia accidental |
