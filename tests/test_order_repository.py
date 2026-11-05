from app.repositories.order_repository import OrderRepository
import pytest 
from app.models.order import Order

@pytest.fixture
def order():
    return Order("123","ab@ab","PENDING")
@pytest.fixture
def rep():
    return OrderRepository()

def test_add_order(order,rep):
    rep.add(order)
    assert rep.orders=={"123":order}

def test_get_order(order,rep):
    rep.add(order)
    assert rep.get("123") == order
    
def test_get_nonexistent_order(rep):
    assert rep.get("a")  is None

def test_add_duplicate_order(order,rep):
    rep.add(order)
    with pytest.raises(ValueError):
        rep.add(order)

def test_list_all_orders(order,rep):
    order2=Order("1234","cd@cd","SHIPPED")
    rep.add(order)
    rep.add(order2)
    assert rep.list_all() ==[order, order2]
    rep.delete("123")
    rep.delete("1234")
    assert rep.list_all()==[]
def test_delete_order(order,rep):
    rep.add(order)
    assert rep.get("123")==order
    rep.delete("123")
    assert rep.get("123")==None

def test_delete_nonexistent_order(rep):
    with pytest.raises(ValueError):
        rep.delete("11")