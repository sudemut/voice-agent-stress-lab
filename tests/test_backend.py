import pytest

from app.api.orders import repository as global_repository
from app.scenarios import SCENARIOS
from app.simulation.backend import InProcessBackend
from app.tools.order_api_client import OrderAPIError


def test_backend_is_seeded_from_fixture():
    with InProcessBackend(SCENARIOS["duplicate"].initial_orders) as backend:
        assert backend.snapshot() == {"ORD-12345": "CANCELLED"}
        order = backend.order_api_client.get_order("ORD-12345")
        assert order["status"] == "CANCELLED"


def test_each_backend_starts_clean():
    orders = SCENARIOS["happy"].initial_orders

    with InProcessBackend(orders) as first:
        first.order_api_client.cancel_order("ORD-12345")
        assert first.snapshot() == {"ORD-12345": "CANCELLED"}

    with InProcessBackend(orders) as second:
        assert second.snapshot() == {"ORD-12345": "PENDING"}


def test_backend_does_not_touch_the_global_repository():
    before = global_repository.get("ORD-12345").status
    with InProcessBackend(SCENARIOS["happy"].initial_orders) as backend:
        backend.order_api_client.cancel_order("ORD-12345")
    assert global_repository.get("ORD-12345").status == before


def test_http_errors_become_order_api_errors():
    with InProcessBackend(SCENARIOS["happy"].initial_orders) as backend:
        with pytest.raises(OrderAPIError) as missing:
            backend.order_api_client.get_order("ORD-99999")
        assert missing.value.status_code == 404
        assert missing.value.detail == "Order not found"

        backend.order_api_client.cancel_order("ORD-12345")
        with pytest.raises(OrderAPIError) as conflict:
            backend.order_api_client.cancel_order("ORD-12345")
        assert conflict.value.status_code == 409


def test_fixture_dicts_are_not_mutated():
    orders = SCENARIOS["happy"].initial_orders
    with InProcessBackend(orders) as backend:
        backend.order_api_client.cancel_order("ORD-12345")
    assert orders[0]["status"] == "PENDING"
