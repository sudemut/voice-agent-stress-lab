import pytest
from unittest.mock import MagicMock
from app.tools.order_api_client import OrderAPIClient
from app.tools.executor import ToolExecutor

def test_execute_get_order():
    mock_client=MagicMock()
    mock_client.get_order.return_value={
        "order_id": "ORD1234",
        "customer_email":"justinbieber@gmail.com",
        "status":"PENDING"
    }
    executer=ToolExecutor(mock_client)
    a=executer.execute("get_order",{"order_id": "ORD-1234"})
    assert a == {
        "order_id": "ORD1234",
        "customer_email":"justinbieber@gmail.com",
        "status":"PENDING"
    }
    mock_client.get_order.assert_called_once_with("ORD-1234")

def test_execute_cancel_order():
    mock_client=MagicMock()
    mock_client.cancel_order.return_value={
        "order_id": "ORD1234",
        "customer_email":"justinbieber@gmail.com",
        "status":"CANCELLED"
    }
    executer=ToolExecutor(mock_client)
    a=executer.execute("cancel_order",{"order_id": "ORD-1234"})
    assert a == {
        "order_id": "ORD1234",
        "customer_email":"justinbieber@gmail.com",
        "status":"CANCELLED"
    }

def test_execute_get_order_status():
    mock_client=MagicMock()
    mock_client.get_order_status.return_value={
        "order_id": "ORD1234",
        "status":"CANCELLED"
    }
    executer=ToolExecutor(mock_client)
    a=executer.execute("get_order_status",{"order_id": "ORD-1234"})
    assert a == {
        "order_id": "ORD1234",
        "status":"CANCELLED"
    }
def test_execute_unknown_tool():
    mock_client=MagicMock()
 
    executer=ToolExecutor(mock_client)
    with pytest.raises(ValueError):
        a=executer.execute("unknowntool",{"order_id": "ORD-1234"})
    mock_client.get_order.assert_not_called()
    mock_client.cancel_order.assert_not_called()
    mock_client.get_order_status.assert_not_called()

def test_execute_missing_order_id():
    mock_client=MagicMock()
    executer=ToolExecutor(mock_client)
    with pytest.raises(ValueError):
        a=executer.execute("get_order",{"order_id": ""})