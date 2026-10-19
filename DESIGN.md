# Notas de Diseño — Branch Queue (Banco Meridional)

## 1. ¿Por qué una cola separada por tipo de servicio es más eficiente que una única cola compartida?

### Problema con una única cola compartida ($O(n)$)
Si todos los clientes se almacenaran en una sola lista o cola general según su orden de llegada, cuando un agente (por ejemplo, de `"deposito"`) quedara libre y ejecutara `call_next("deposito")`, el sistema tendría que:
1. Recorrer la lista desde el principio elemento por elemento buscando el primer ticket cuyo `service_type` sea `"deposito"`.
2. Si delante hay $n$ clientes esperando por `"retiro"` o `"gestion_cuenta"`, la búsqueda tarda un tiempo proporcional a $n$, es decir, **$O(n)$**.
3. Además, eliminar un elemento que se encuentra en medio de una lista o `deque` requiere desplazar los elementos restantes, lo cual también tiene un costo **$O(n)$**.

### Ventaja de colas separadas por servicio ($O(1)$)
En `BranchQueue` utilizamos un diccionario (`self._queues`) donde cada clave es un tipo de servicio (`"deposito"`, `"retiro"`, `"gestion_cuenta"`) y su valor es una estructura `collections.deque` dedicada exclusivamente a ese servicio:
- **Acceso al servicio en $O(1)$**: Buscar la cola correspondiente en un diccionario por su clave (`self._queues[service_type]`) es instantáneo ($O(1)$).
- **Desencolado en $O(1)$**: Como la cola de ese servicio solo contiene clientes de ese mismo servicio ordenados por llegada (FIFO), el siguiente cliente siempre está en el frente (`queue[0]`). Extraerlo mediante `popleft()` en un `deque` toma tiempo constante **$O(1)$**, sin importar si hay 10 o 10,000 personas esperando en los otros servicios.
- **Numeración global preservada**: El contador `self._next_ticket_number` es único en toda la instancia de `BranchQueue`, por lo que los números de ticket siguen siendo globalmente secuenciales ($1, 2, 3, \dots$) aunque se almacenen en colas separadas.

---

## 2. Concurrencia: ¿Qué ocurriría si dos agentes del mismo servicio llamasen a `call_next` al mismo tiempo?

### El riesgo: Condición de carrera (*Race Condition*)
Imaginemos que dos agentes de `"deposito"` (Agente A y Agente B) presionan el botón de llamar al siguiente cliente en el mismo instante cuando el ticket `#5` está al frente de la cola:

Si `call_next` estuviera diseñado separando la **lectura** de la **eliminación** en dos pasos no sincronizados:
1. El Agente A lee el primer elemento de la cola (`ticket = queue[0]`, que es `#5`).
2. Antes de que el Agente A lo elimine de la cola, el Agente B también lee el frente de la cola (`ticket = queue[0]`, que sigue siendo `#5`).
3. Ambos agentes reciben el ticket `#5` y llaman al mismo cliente a dos ventanillas distintas, o bien el segundo `popleft()` termina eliminando por error al ticket siguiente (`#8`) sin que nadie lo atienda.

### ¿Qué mutación de estado debe ocurrir primero?
Para garantizar que el mismo cliente **nunca** sea llamado dos veces:
1. **La extracción/remoción del ticket de la cola (`popleft()`) debe ocurrir de forma atómica e indivisible antes de entregar el ticket al agente.** Es decir, la operación de *"obtener quién sigue"* y *"retirarlo de la lista de espera"* debe ser una única mutación de estado (`ticket = queue.popleft()`), nunca un `peek` seguido de un `remove`.
2. **Bloqueo de exclusión mutua (Lock / Mutex) por cola**: En un entorno multihilo o distribuido real, el acceso a `call_next` debe protegerse con un cerrojo (`threading.Lock` en Python o `SELECT ... FOR UPDATE SKIP LOCKED` en base de datos). Así, el primer agente adquiere el candado, verifica que la cola no esté vacía, ejecuta la mutación `popleft()` retirando el ticket de la cola en primer lugar, libera el candado y devuelve el ticket. Cuando el segundo agente entra, el primer ticket ya no existe en la cola y recibe inmediatamente el siguiente cliente disponible (o el aviso de cola vacía).
