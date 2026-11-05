import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.orders import get_repository
from app.repositories.order_repository import OrderRepository
from app.models.order import Order

@pytest.fixture
def test_repository():
    repo = OrderRepository()
    repo.add(Order("ORD-TEST-001", "alice@example.com", "PENDING"))
    return repo

@pytest.fixture
def client(test_repository):

    def override_get_repository():
        return test_repository

    app.dependency_overrides[get_repository] = override_get_repository

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.pop(get_repository, None)

def test_get_existing_order(client):
    resp= client.get("/orders/ORD-TEST-001")
    data=resp.json()
    assert resp.status_code==200
    assert data["order_id"] =="ORD-TEST-001"  
    assert data["status"]=="PENDING"
    assert data["customer_email"]=="alice@example.com"

def test_get_nonexistent_order(client):
    resp=client.get("/orders/UNKNOWN")
    assert resp.status_code==404
    assert resp.json()["detail"] == "Order not found"

def test_cancel_order(client):
    resp=client.post("/orders/ORD-TEST-001/cancel")
    assert resp.status_code==200
    assert resp.json()["status"] =="CANCELLED"
    new_resp=client.get("/orders/ORD-TEST-001")
    assert new_resp.json()=={"order_id":"ORD-TEST-001","customer_email":"alice@example.com","status":"CANCELLED"}

def test_cancel_twice(client):
    resp=client.post("/orders/ORD-TEST-001/cancel")
    assert resp.status_code==200
    new_resp=client.post("/orders/ORD-TEST-001/cancel")
    assert new_resp.status_code==409
    current_resp= client.get("/orders/ORD-TEST-001")
    assert current_resp.json()["status"]=="CANCELLED"

def  test_cancel_nonexistent_order(client):
    resp=client.post("/orders/ORD-TEST-002/cancel")
    assert resp.status_code==404

def test_get_order_status(client):
    resp=client.get("/orders/ORD-TEST-001")
    assert resp.json()["status"]=="PENDING"
    new_resp=client.post("/orders/ORD-TEST-001/cancel")
    new_resp=client.get("/orders/ORD-TEST-001")
    assert new_resp.json()["status"]=="CANCELLED"