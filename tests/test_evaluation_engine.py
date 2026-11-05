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
from app.evaluation.engine import EvaluationEngine

def test_engine_judge_integration():
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
    scenario=TestScenario(1,"order cancellation","cancel an order",{},"Order cancelled",5)
    runner=SimulationRunner(scenario)
    runner.start_simulation()
    runner.complete_simulation()
    engine=EvaluationEngine(client)
    result=engine.evaluate(runner)


    assert result.reasoning=="The agent understood the request and responded appropriately."
    assert isinstance(result, EvaluationResult)
    assert result.task_success == "NOT_VERIFIED"
    assert result.scenario_id == 1
    mock_gemini.generate_evaluation.assert_called_once()

def test_engine_completed():
    # 1. Sahte Judge oluştur
    mock_judge = MagicMock()

    # 2. Judge'ın döndürmesini istediğimiz sonucu oluştur
    expected_result = EvaluationResult(
        scenario_id=1,
        task_success="NOT_VERIFIED",
        quality_scores={
            "relevance": 5,
            "coherence": 5,
            "helpfulness": 4,
            "repetition": 5
        },
        reasoning="The agent understood the request.",
        evidence=["The agent requested the order number."],
        failure_reasons=[]
    )

    # 3. Sahte Judge'a ne döndüreceğini söyle
    mock_judge.evaluate.return_value = expected_result

    # 4. Gerçek Runner oluştur
    scenario = TestScenario(
        1, "order cancellation", "cancel an order",
        {}, "Order cancelled", 5
    )

    runner = SimulationRunner(scenario)
    runner.start_simulation()
    runner.complete_simulation()

    # 5. Gerçek Engine'e sahte Judge ver
    engine = EvaluationEngine(mock_judge)

    # 6. Engine'i çalıştır
    result = engine.evaluate(runner)

    # 7. Sonucu doğrula
    assert result is expected_result

    mock_judge.evaluate.assert_called_once_with(
        runner.scenario,
        runner.conversation_history
    )

def test_engine_judge_failure():
    mock_judge = MagicMock()
    mock_judge.evaluate.side_effect = RuntimeError(
    "Gemini API unavailable"
)

    scenario = TestScenario(
        1, "order cancellation", "cancel an order",
        {}, "Order cancelled", 5
    )

    runner = SimulationRunner(scenario)
    runner.start_simulation()
    runner.complete_simulation()
    engine=EvaluationEngine(mock_judge)
    with pytest.raises(RuntimeError):
        engine.evaluate(runner)
    assert runner.status=="COMPLETED"

def test_engine_running():
    mock_judge = MagicMock()
    scenario = TestScenario(
        1, "order cancellation", "cancel an order",
        {}, "Order cancelled", 5
    )
    runner = SimulationRunner(scenario)
    runner = SimulationRunner(scenario)
    runner.start_simulation()
    engine=EvaluationEngine(mock_judge)
    with pytest.raises(ValueError):
        engine.evaluate(runner)
    mock_judge.evaluate.assert_not_called()