import pytest
from unittest.mock import MagicMock

from app.tools.order_api_client import OrderAPIError
from app.tools.tool_calling_service import ToolCallingService, ToolStepLimitExceeded
from tests.fakes import ScriptedSupportLLM, text, tool_call

HISTORY = [{"role": "user", "content": "Please cancel my order ORD-12345."}]


def run(service):
    return service.run(
        system_prompt="You are a customer support agent.",
        conversation_history=HISTORY,
        tools=MagicMock(),
    )


def test_normal_message():
    llm = ScriptedSupportLLM([text("Could you please provide your order number?")])
    mock_executer = MagicMock()

    result = run(ToolCallingService(llm, mock_executer))

    assert result["type"] == "message"
    assert result["content"] == "Could you please provide your order number?"
    assert result["tool_calls"] == []
    mock_executer.execute.assert_not_called()


def test_successful_tool_call():
    expected_order = {
        "order_id": "ORD-12345",
        "customer_email": "alice@example.com",
        "status": "CANCELLED"
    }
    llm = ScriptedSupportLLM([
        tool_call("cancel_order", order_id="ORD-12345"),
        text("Your order ORD-12345 has been successfully cancelled."),
    ])
    mock_executer = MagicMock()
    mock_executer.execute.return_value = expected_order

    result = run(ToolCallingService(llm, mock_executer))

    assert result["content"] == "Your order ORD-12345 has been successfully cancelled."
    assert result["tool_calls"] == [{
        "name": "cancel_order",
        "arguments": {"order_id": "ORD-12345"},
        "response": {"success": True, "result": expected_order},
    }]
    mock_executer.execute.assert_called_once_with(
        "cancel_order",
        {"order_id": "ORD-12345"}
    )


def test_multiple_sequential_tool_calls():
    llm = ScriptedSupportLLM([
        tool_call("get_order", order_id="ORD-12345"),
        tool_call("cancel_order", order_id="ORD-12345"),
        tool_call("get_order_status", order_id="ORD-12345"),
        text("Cancelled and confirmed."),
    ])
    mock_executer = MagicMock()
    mock_executer.execute.side_effect = [
        {"status": "PENDING"},
        {"status": "CANCELLED"},
        {"status": "CANCELLED"},
    ]

    result = run(ToolCallingService(llm, mock_executer))

    assert [call["name"] for call in result["tool_calls"]] == [
        "get_order", "cancel_order", "get_order_status"
    ]
    assert result["content"] == "Cancelled and confirmed."


def test_backend_error_is_returned_to_model_as_tool_result():
    llm = ScriptedSupportLLM([
        tool_call("get_order", order_id="ORD-99999"),
        text("I could not find that order."),
    ])
    mock_executer = MagicMock()
    mock_executer.execute.side_effect = OrderAPIError(404, "Order not found")

    result = run(ToolCallingService(llm, mock_executer))

    assert result["tool_calls"][0]["response"] == {
        "success": False,
        "error": "404: Order not found",
        "status_code": 404,
    }


def test_tool_step_limit_raises_dedicated_error():
    llm = ScriptedSupportLLM([tool_call("get_order", order_id="ORD-1")] * 3)
    mock_executer = MagicMock()
    mock_executer.execute.return_value = {"status": "PENDING"}

    with pytest.raises(ToolStepLimitExceeded):
        run(ToolCallingService(llm, mock_executer, max_tool_steps=2))


def test_invalid_max_tool_steps():
    with pytest.raises(ValueError):
        ToolCallingService(MagicMock(), MagicMock(), max_tool_steps=0)
