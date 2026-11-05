from app.models.order import Order
import pytest
@pytest.fixture
def sample_order():
    return Order("O1234","alice@gmail.com","PENDING")

def test_cancel_pending_order(sample_order):
    sample_order.cancel()
    assert sample_order.status=="CANCELLED"
def test_create_valid_order(sample_order):
    assert sample_order.order_id=="O1234"
    assert sample_order.customer_email=="alice@gmail.com"
    assert sample_order.status=="PENDING"
def test_can_cancel_pending(sample_order):
    assert sample_order.can_cancel()==True

def test_cancel_shipped_order():
    order=Order("O1234","alice@gmail.com","SHIPPED")
    with pytest.raises(ValueError):
        order.cancel()
    assert order.status=="SHIPPED"
    
def test_cancel_twice(sample_order):
    sample_order.cancel()
    with pytest.raises(ValueError):
        sample_order.cancel()
    assert sample_order.status=="CANCELLED"


def test_invalid_order_status(sample_order):
    with pytest.raises(ValueError):
        Order("O1234", "alice@gmail.com", "INVALID")



def test_order_to_dict(sample_order):
    sample_order.cancel()
    assert sample_order.to_dict()=={"order_id":"O1234", "customer_email": "alice@gmail.com", "status": "CANCELLED"}