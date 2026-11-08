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
from app.models.evaluation_result import EvaluationResult
from app.evaluation.llm_judge import LLMJudge

def test_llm_judge_success():
    our_testsc= TestScenario(1,"order cancellation","cancel an order",{},"Order cancelled",5)
    conversation_history= [
    {
        "role": "customer",
        "content": "I want to cancel my order."
    },
    {
        "role": "agent",
        "content": "Could you provide your order number?"
    },
    {
        "role": "customer",
        "content": "ORD-12345"
    },
    {
        "role": "agent",
        "content": "I will help you with that."
    }
]
    mock_gemini=MagicMock()
    mock_gemini.generate_evaluation.return_value={
    "quality_scores": {
        "relevance": 5,
        "coherence": 5,
        "helpfulness": 4,
        "repetition": 5
    },
    "reasoning": "The agent understood the request and responded appropriately.",
    "evidence": [
        "The agent requested the order number."
    ],
    "failure_reasons": []
}
    client=LLMJudge(mock_gemini)
    ev_result=client.evaluate(our_testsc,conversation_history)
    assert ev_result.evidence==["The agent requested the order number."]
    assert ev_result.failure_reasons==[]
    assert ev_result.quality_scores== {
        "relevance": 5,
        "coherence": 5,
        "helpfulness": 4,
        "repetition": 5
    }
    
    assert ev_result.reasoning=="The agent understood the request and responded appropriately."
    assert isinstance(ev_result, EvaluationResult)
    assert not hasattr(ev_result, "task_success")
    assert ev_result.scenario_id == 1
    mock_gemini.generate_evaluation.assert_called_once()

def test_prompt_tells_judge_not_to_decide_task_success():
    scenario = TestScenario(1, "order cancellation", "cancel an order", {}, "Order cancelled", 5)
    prompt = LLMJudge(MagicMock()).build_prompt(
        scenario,
        [{"role": "agent", "content": "Hello"}]
    )
    assert "decided separately by deterministic checks" in prompt
    assert "Score only how the agent communicated" in prompt


def test_invalid_response():
    our_testsc= TestScenario(1,"order cancellation","cancel an order",{},"Order cancelled",5)
    conversation_history= [
    {
        "role": "customer",
        "content": "I want to cancel my order."
    },
    {
        "role": "agent",
        "content": "Could you provide your order number?"
    },
    {
        "role": "customer",
        "content": "ORD-12345"
    },
    {
        "role": "agent",
        "content": "I will help you with that."
    }
]
    mock_gemini=MagicMock()
    mock_gemini.generate_evaluation.return_value={
    "quality_scores": {
        "relevance": 10,
        "coherence": 5,
        "helpfulness": 4,
        "repetition": 5
    },
    "reasoning": "Good conversation.",
    "evidence": [],
    "failure_reasons": []
}
    client=LLMJudge(mock_gemini)
    with pytest.raises(ValueError):
        client.evaluate(our_testsc,conversation_history)

def test_api_failure():
    our_testsc= TestScenario(1,"order cancellation","cancel an order",{},"Order cancelled",5)
    conversation_history= [
    {
        "role": "customer",
        "content": "I want to cancel my order."
    },
    {
        "role": "agent",
        "content": "Could you provide your order number?"
    },
    {
        "role": "customer",
        "content": "ORD-12345"
    },
    {
        "role": "agent",
        "content": "I will help you with that."
    }
]
    mock_gemini=MagicMock()
    mock_gemini.generate_evaluation.side_effect = RuntimeError(
    "Gemini API unavailable"
)
    client=LLMJudge(mock_gemini)
    with pytest.raises(RuntimeError):
        client.evaluate(our_testsc,conversation_history)