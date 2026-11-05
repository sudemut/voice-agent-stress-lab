import pytest
from app.agents.base import BaseAgent
from app.agents.customer import CustomerAgent
from app.agents.support import SupportAgent
from app.llm.client import LLMClient
from app.llm.openai_client import OpenAIClient
from unittest.mock import MagicMock

from unittest.mock import MagicMock

from app.models.scenario import TestScenario
from app.agents.customer import CustomerAgent


def test_customer_agent_generate_response():
    # 1. Mock LLM oluştur
    mock_client = MagicMock()
    mock_client.generate.return_value = "I want to book an appointment."

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
    assert response == "I want to book an appointment."

    # 6. LLM'in doğru parametrelerle çağrıldığını doğrula
    mock_client.generate.assert_called_once_with(
        system_prompt,
        conversation_history
    )
def test_support_agent_generate_response():
     # 1. Mock LLM oluştur
        mock_client = MagicMock()
        mock_client.generate.return_value = "I want to book an appointment."
    
        # 2. Test senaryosu oluştur
        scenario = TestScenario(
            1, "Appointment Booking",
            "Book an appointment",
            {}, "success", 5
        )
    
        # 3. CustomerAgent oluştur
        system_prompt = "You are a customer booking an appointment."
    
        customer = SupportAgent(
            "Customer",
            system_prompt,
            mock_client,
            scenario
        )
    
        # 4. Agent'tan yanıt al
        conversation_history = []
        response = customer.generate_response(conversation_history)
    
        # 5. Yanıtı doğrula
        assert response == "I want to book an appointment."
    
        # 6. LLM'in doğru parametrelerle çağrıldığını doğrula
        mock_client.generate.assert_called_once_with(
            system_prompt,
            conversation_history
        )