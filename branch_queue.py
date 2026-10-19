from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

VALID_SERVICES = ("deposito", "retiro", "gestion_cuenta")


@dataclass
class Ticket:
    """Representa un ticket de atención emitido a un cliente."""
    number: int
    client_name: str
    service_type: str
    issued_at: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        timestamp = self.issued_at.strftime("%H:%M:%S")
        return f"[#{self.number}] {self.client_name} ({self.service_type}) - {timestamp}"


class BranchQueue:
    """Gestor de colas de sucursal con una cola FIFO independiente por tipo de servicio."""

    def __init__(self) -> None:
        self._queues: Dict[str, deque[Ticket]] = {
            service: deque() for service in VALID_SERVICES
        }
        self._next_ticket_number: int = 1

    def _validate_service(self, service_type: str) -> str:
        normalized = service_type.strip().lower() if isinstance(service_type, str) else ""
        if normalized not in self._queues:
            valid_str = ", ".join(VALID_SERVICES)
            raise ValueError(
                f"Tipo de servicio inválido: '{service_type}'. "
                f"Opciones válidas: {valid_str}."
            )
        return normalized

    def issue_ticket(self, client_name: str, service_type: str) -> Ticket:
        """Crea y encola un ticket en la cola de servicio correspondiente."""
        if not isinstance(client_name, str) or not client_name.strip():
            raise ValueError("El nombre del cliente no puede estar vacío.")

        normalized_service = self._validate_service(service_type)
        ticket = Ticket(
            number=self._next_ticket_number,
            client_name=client_name.strip(),
            service_type=normalized_service,
        )
        self._next_ticket_number += 1
        self._queues[normalized_service].append(ticket)
        return ticket

    def call_next(self, service_type: str) -> Ticket:
        """Desencola y devuelve el siguiente cliente para el tipo de servicio."""
        normalized_service = self._validate_service(service_type)
        queue = self._queues[normalized_service]
        if not queue:
            raise LookupError(
                f"No hay clientes en espera para el servicio '{normalized_service}'."
            )
        return queue.popleft()

    def peek_next(self, service_type: str) -> Optional[Ticket]:
        """Devuelve el siguiente cliente para un tipo de servicio sin retirarlo de la cola."""
        normalized_service = self._validate_service(service_type)
        queue = self._queues[normalized_service]
        if not queue:
            return None
        return queue[0]

    def list_waiting(self) -> Dict[str, List[Ticket]]:
        """Devuelve un diccionario con cada servicio y su lista ordenada de tickets en espera."""
        return {
            service: list(queue) for service, queue in self._queues.items()
        }

    def stats(self) -> Dict[str, int]:
        """Devuelve el número de clientes en espera por servicio y el total general."""
        counts = {
            service: len(queue) for service, queue in self._queues.items()
        }
        counts["total"] = sum(counts.values())
        return counts


def prompt_service_type() -> str:
    """Muestra las opciones de servicio y devuelve la entrada del usuario."""
    print("\nTipos de servicio disponibles:")
    print("  1. deposito")
    print("  2. retiro")
    print("  3. gestion_cuenta")
    choice = input("Seleccione el servicio (1-3 o escriba el nombre): ").strip().lower()
    mapping = {
        "1": "deposito",
        "2": "retiro",
        "3": "gestion_cuenta",
    }
    return mapping.get(choice, choice)


def main() -> None:
    """Bucle interactivo CLI para gestionar las colas de la sucursal."""
    branch_queue = BranchQueue()

    while True:
        print("\n=== Banco Meridional — Gestor de Colas ===")
        print("1. Emitir nuevo ticket")
        print("2. Llamar al siguiente cliente")
        print("3. Ver siguiente cliente sin llamarlo (Peek)")
        print("4. Ver lista de espera completa")
        print("5. Ver estadísticas de la cola")
        print("6. Salir")

        option = input("Seleccione una opción (1-6): ").strip()

        if option == "1":
            client_name = input("Nombre del cliente: ").strip()
            service_type = prompt_service_type()
            try:
                ticket = branch_queue.issue_ticket(client_name, service_type)
                print(f"✅ Ticket emitido: {ticket}")
            except ValueError as err:
                print(f"⚠️ Error: {err}")

        elif option == "2":
            service_type = prompt_service_type()
            try:
                ticket = branch_queue.call_next(service_type)
                print(f"📢 Llamando a: {ticket}")
            except (ValueError, LookupError) as err:
                print(f"⚠️ {err}")

        elif option == "3":
            service_type = prompt_service_type()
            try:
                ticket = branch_queue.peek_next(service_type)
                if ticket is None:
                    print(f"ℹ️ No hay clientes esperando para '{service_type}'.")
                else:
                    print(f"👀 Siguiente en '{service_type}': {ticket}")
            except ValueError as err:
                print(f"⚠️ Error: {err}")

        elif option == "4":
            waiting = branch_queue.list_waiting()
            print("\n--- Clientes en espera por servicio ---")
            for service, tickets in waiting.items():
                print(f"\n[{service.upper()}] ({len(tickets)} en espera):")
                if not tickets:
                    print("  (Sin clientes en espera)")
                else:
                    for idx, ticket in enumerate(tickets, start=1):
                        print(f"  {idx}. {ticket}")

        elif option == "5":
            current_stats = branch_queue.stats()
            print("\n--- Estadísticas de la sucursal ---")
            for service in VALID_SERVICES:
                print(f"  {service}: {current_stats[service]} en espera")
            print(f"  TOTAL: {current_stats['total']} en espera")

        elif option == "6":
            print("Saliendo del gestor de colas. ¡Hasta pronto!")
            break

        else:
            print("⚠️ Opción no válida. Por favor, elija un número del 1 al 6.")


if __name__ == "__main__":
    main()

