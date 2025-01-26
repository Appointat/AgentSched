import time
from threading import Lock
from typing import Any, Dict, List


class ConnectionPool:
    """A simple connection pool for managing connections to LLM models.

    Args:
        max_connections (int): Maximum number of connections to maintain. (default: 10)
        available_connections (List): List of available connections.
        in_use_connections (Dict): Dictionary of connections currently in use.
        lock (Lock): Threading lock for managing concurrent access to the pool.
    """

    def __init__(self, max_connections: int = 10):
        self.max_connections: int = max_connections
        self.available_connections: List[Any] = []
        self.in_use_connections: Dict[Any, float] = {}
        self.lock: Lock = Lock()

    def get_connection(self) -> Any:
        """Get a connection from the pool, creating a new one if necessary."""
        with self.lock:
            if self.available_connections:
                conn = self.available_connections.pop()
            elif len(self.in_use_connections) < self.max_connections:
                conn = self._create_new_connection()
            else:
                conn = None

            if conn:
                self.in_use_connections[conn] = time.time()
            return conn

    def release_connection(self, conn: Any) -> None:
        """Release a connection back to the pool."""
        with self.lock:
            if conn in self.in_use_connections:
                del self.in_use_connections[conn]
                self.available_connections.append(conn)

    def _create_new_connection(self) -> Any:
        # TODO: Implement actual connection creation logic
        return object()

    def cleanup_stale_connections(self, max_idle_time: float = 300) -> None:
        """Remove stale connections that have been idle for too long."""
        current_time = time.time()
        with self.lock:
            stale_conns = [
                conn
                for conn, start_time in self.in_use_connections.items()
                if current_time - start_time > max_idle_time
            ]
            for conn in stale_conns:
                del self.in_use_connections[conn]
                self.available_connections.append(conn)
