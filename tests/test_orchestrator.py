import pytest
from app.models.agent_result import AgentResult
from app.agents.base import BaseAgent
from app.agents.customer import CustomerAgent
from app.agents.support import SupportAgent
from app.llm.client import LLMClient
from app.llm.openai_client import OpenAIClient
from unittest.mock import MagicMock
from app.models.scenario import TestScenario
from app.agents.customer import CustomerAgent
from app.simulation.runner import SimulationRunner
from app.simulation.orchestrator import ConversationOrchestrator

def test_support_failure_marks_sim_failed():
    mock_client1 = MagicMock()
    mock_client1.generate.return_value = "I want to book an appointment."
    mock_client2=MagicMock()
    mock_client2.generate.side_effect = [
    "Could you provide your order number?",
    RuntimeError("Gemini API unavailable")
]
    
        # 2. Test senaryosu oluştur
    scenario = TestScenario(
            1, "Appointment Booking",
            "Book an appointment",
            {}, "success", 3
        )
    
        # 3. CustomerAgent oluştur
    system_prompt = "You are a customer booking an appointment."
    system_prompt2="You are an voice ai agent"
    
    customer = CustomerAgent(
            "customer",
            system_prompt,
            mock_client1,
            scenario
        )
    support=SupportAgent(
        "agent",
        system_prompt2,
        mock_client2,
    )
    

    runner=SimulationRunner(scenario)
    orchestrator = ConversationOrchestrator(
    customer_agent=customer,
    support_agent=support,
    runner=runner
)
    orchestrator.run()

    assert runner.status=="FAILED"
    assert runner.current_turn==0
    assert len(runner.conversation_history)==0



def test_customer_early_termination():
    customer = MagicMock()
    support = MagicMock()

    customer.generate_response.return_value = AgentResult(
        message="I don't need help anymore. Goodbye!",
        end_conversation=True
    )

    scenario = TestScenario(
        1, "Early Termination",
        "Test conversation termination",
        {}, "Conversation ended", 10
    )

    runner = SimulationRunner(scenario)
    orchestrator = ConversationOrchestrator(customer, support, runner)

    orchestrator.run()

    assert runner.status == "COMPLETED"
    assert runner.termination_reason == "AGENT_ENDED"
    assert runner.current_turn == 0
    assert len(runner.conversation_history) == 1

    support.generate_response.assert_not_called()

def test_support_early_termination():
    customer = MagicMock()
    support = MagicMock()

    customer.generate_response.side_effect = [
        AgentResult("I want to book an appointment.", False),
        AgentResult("Tomorrow at 2 PM, please.", False)
    ]

    support.generate_response.side_effect = [
        AgentResult("What date and time works for you?", False),
        AgentResult("Thanks. That is all for now. Goodbye!", True)
    ]

    scenario = TestScenario(
        2, "Support Termination",
        "Test support early termination",
        {}, "Conversation ended", 10
    )

    runner = SimulationRunner(scenario)
    orchestrator = ConversationOrchestrator(customer, support, runner)

    orchestrator.run()

    assert runner.status == "COMPLETED"
    assert runner.termination_reason == "AGENT_ENDED"
    assert runner.current_turn == 2
    assert len(runner.conversation_history) == 4

    assert customer.generate_response.call_count == 2
    assert support.generate_response.call_count == 2
