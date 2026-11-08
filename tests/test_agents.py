from unittest.mock import MagicMock

from app.agents.customer import CustomerAgent
from app.agents.support import SupportAgent
from app.models.agent_result import AgentResult
from app.models.scenario import TestScenario


def test_customer_agent_generate_response():
    # 1. Mock LLM oluştur
    mock_client = MagicMock()
    mock_client.generate_structured.return_value = {
        "message": "I want to book an appointment.",
        "end_conversation": False,
    }

    # 2. Test senaryosu oluştur
    scenario = TestScenario(
        1, "Appointment Booking",
        "Book an appointment",
        {}, "success", 5
    )

    # 3. CustomerAgent oluştur
    system_prompt = "You are a customer booking an appointment."

    customer = CustomerAgent(
        "Customer",
        system_prompt,
        mock_client,
        scenario
    )

    # 4. Agent'tan yanıt al
    conversation_history = []
    response = customer.generate_response(conversation_history)

    # 5. Yanıtı doğrula
    assert isinstance(response, AgentResult)
    assert response.message == "I want to book an appointment."
    assert response.end_conversation is False

    # 6. LLM'in doğru parametrelerle çağrıldığını doğrula
    mock_client.generate_structured.assert_called_once_with(
        system_prompt,
        conversation_history
    )


def test_support_agent_without_tools_uses_structured_generation():
    mock_client = MagicMock()
    mock_client.generate_structured.return_value = {
        "message": "How can I help you?",
        "end_conversation": False,
    }
    system_prompt = "You are a support agent."

    support = SupportAgent("Support", system_prompt, mock_client)

    response = support.generate_response([])

    assert response.message == "How can I help you?"
    assert response.tool_calls == []
    mock_client.generate_structured.assert_called_once_with(system_prompt, [])


def test_support_agent_with_tools_returns_tool_calls():
    tool_service = MagicMock()
    tool_calls = [{"name": "get_order", "arguments": {"order_id": "ORD-1"}, "response": {}}]
    tool_service.run.return_value = {
        "type": "message",
        "content": "Your order is pending.",
        "tool_calls": tool_calls,
    }
    tools = MagicMock()

    support = SupportAgent("Support", "prompt", MagicMock(), tool_service, tools)
    response = support.generate_response([{"role": "user", "content": "Status?"}])

    assert response.message == "Your order is pending."
    assert response.tool_calls == tool_calls
    tool_service.run.assert_called_once_with(
        system_prompt="prompt",
        conversation_history=[{"role": "user", "content": "Status?"}],
        tools=tools,
    )
