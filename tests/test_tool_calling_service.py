import pytest
from unittest.mock import MagicMock
from app.tools.tool_calling_service import ToolCallingService
from app.llm.client import LLMClient
from app.llm.gemini_client import GeminiClient





def test_normal_message():

    mock_gemini = MagicMock()

    mock_response = MagicMock()
    mock_response.function_calls = []
    mock_response.text = "Could you please provide your order number?"


    mock_gemini.generate_with_tools.return_value = mock_response

    mock_executer = MagicMock()

    service = ToolCallingService(mock_gemini, mock_executer)

    result = service.run(
        system_prompt="You are a customer support agent.",
        conversation_history=[
            {"role": "user", "content": "I want to cancel my order."}
        ],
        tools=MagicMock()
    )

    assert result["type"] == "message"
    assert result["content"] == "Could you please provide your order number?"
    assert result["tool_calls"] == []

    mock_executer.execute.assert_not_called()
    mock_gemini.generate_with_tools.assert_called_once()

def test_successful_tool_call():
    mock_gemini = MagicMock()
    mock_executer = MagicMock()

    mock_function_call = MagicMock()
    mock_function_call.name = "cancel_order"
    mock_function_call.args = {"order_id": "ORD-12345"}

    mock_response = MagicMock()
    mock_response.function_calls = [mock_function_call]
    mock_response.candidates[0].content = MagicMock()
    mock_gemini.generate_with_tools.return_value = mock_response

    expected_order = {
        "order_id": "ORD-12345",
        "customer_email": "alice@example.com",
        "status": "CANCELLED"
    }

    mock_executer.execute.return_value = expected_order

    mock_gemini.generate_after_tool.return_value = (
        "Your order ORD-12345 has been successfully cancelled."
    )

    service = ToolCallingService(mock_gemini, mock_executer)

    system_prompt = "You are a customer support agent."

    conversation_history = [
        {
            "role": "user",
            "content": "Please cancel my order ORD-12345."
        }
    ]

    tools = MagicMock()

    result = service.run(
        system_prompt=system_prompt,
        conversation_history=conversation_history,
        tools=tools
    )

    assert result["type"] == "message"

    assert result["content"] == (
        "Your order ORD-12345 has been successfully cancelled."
    )

    assert len(result["tool_calls"]) == 1

    assert result["tool_calls"][0]["name"] == "cancel_order"

    assert result["tool_calls"][0]["arguments"] == {
        "order_id": "ORD-12345"
    }

    assert result["tool_calls"][0]["response"] == {
        "success": True,
        "result": expected_order
    }

    mock_executer.execute.assert_called_once_with(
        "cancel_order",
        {"order_id": "ORD-12345"}
    )
    mock_gemini.generate_after_tool.assert_called_once_with(
        system_prompt=system_prompt,
        conversation_history=conversation_history,
        tools=tools,
        model_content=mock_response.candidates[0].content,
        tool_name="cancel_order",
        tool_response={
            "success": True,
            "result": expected_order
        }
    )
def test_multiple_function_calls():
    mock_gemini = MagicMock()
    mock_executer = MagicMock()

    mock_function_call = MagicMock()
    mock_function_call.name = "cancel_order"
    mock_function_call.args = {"order_id": "ORD-12345"}

    mock_response = MagicMock()
    mock_response.function_calls = [mock_function_call]
    mock_response.candidates[0].content = MagicMock()

    mock_gemini.generate_with_tools.return_value = mock_response

    expected_order = {
        "order_id": "ORD-12345",
        "customer_email": "alice@example.com",
        "status": "CANCELLED"
    }

    mock_executer.execute.return_value = expected_order

    mock_gemini.generate_after_tool.return_value = (
        "Your order ORD-12345 has been successfully cancelled."
    )

    service = ToolCallingService(mock_gemini, mock_executer)

    system_prompt = "You are a customer support agent."

    conversation_history = [
        {
            "role": "user",
            "content": "Please cancel my order ORD-12345."
        }
    ]

    tools = MagicMock()

    result = service.run(
        system_prompt=system_prompt,
        conversation_history=conversation_history,
        tools=tools
    )
    assert result["type"] == "message"

    assert result["content"] == (
        "Your order ORD-12345 has been successfully cancelled."
    )

    assert len(result["tool_calls"]) == 1

    assert result["tool_calls"][0]["name"] == "cancel_order"

    assert result["tool_calls"][0]["arguments"] == {
        "order_id": "ORD-12345"
    }

    assert result["tool_calls"][0]["response"] == {
        "success": True,
        "result": expected_order
    }
    mock_executer.execute.assert_called_once_with(
        "cancel_order",
        {"order_id": "ORD-12345"}
    )

    mock_gemini.generate_after_tool.assert_called_once_with(
        system_prompt=system_prompt,
        conversation_history=conversation_history,
        tools=tools,
        model_content=mock_response.candidates[0].content,
        tool_name="cancel_order",
        tool_response={
            "success": True,
            "result": expected_order
        }
    )