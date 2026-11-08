from fastapi.testclient import TestClient

from app.api.orders import get_repository
from app.api.server import create_app
from app.models.order import Order
from app.repositories.order_repository import OrderRepository
from app.tools.order_api_client import OrderAPIClient


class InProcessBackend:
    """A fresh order backend for exactly one simulation run.

    Each instance builds its own FastAPI app and OrderRepository, seeds it
    from the scenario fixture, and serves it through TestClient. Runs never
    share state, so no server process or manual reset is needed.

    Usage:
        with InProcessBackend(spec.initial_orders) as backend:
            backend.order_api_client.get_order("ORD-12345")
            backend.snapshot()
    """

    BASE_URL = "http://testserver"

    def __init__(self, initial_orders):
        self.repository = OrderRepository()
        for order in initial_orders:
            self.repository.add(
                Order(
                    order_id=order["order_id"],
                    customer_email=order["customer_email"],
                    status=order["status"],
                )
            )

        self.app = create_app()
        self.app.dependency_overrides[get_repository] = lambda: self.repository
        self._test_client = None
        self.order_api_client = None

    def __enter__(self):
        self._test_client = TestClient(self.app)
        self.order_api_client = OrderAPIClient(
            base_url=self.BASE_URL,
            http_client=self._test_client,
        )
        return self

    def __exit__(self, exc_type, exc, traceback):
        self._test_client.close()
        self.app.dependency_overrides.clear()
        return False

    def snapshot(self):
        """Order statuses read straight from the repository, not via tools."""
        return {
            order.order_id: order.status
            for order in self.repository.list_all()
        }
