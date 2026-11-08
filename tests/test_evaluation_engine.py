import pytest
from unittest.mock import MagicMock

from app.evaluation.engine import EvaluationEngine
from app.evaluation.llm_judge import LLMJudge
from app.evaluation.verifier import VerificationCriteria
from app.models.evaluation_result import EvaluationResult
from app.models.scenario import TestScenario
from app.simulation.runner import SimulationRunner

JUDGE_OUTPUT = {
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

BACKEND = {"ORD-12345": "PENDING"}


def finished_runner():
    scenario = TestScenario(
        1, "order cancellation", "cancel an order",
        {}, "Order cancelled", 5
    )
    runner = SimulationRunner(scenario)
    runner.start_simulation()
    runner.add_message("customer", "Cancel my order")
    runner.add_message("agent", "Could you provide your order number?")
    runner.complete_simulation()
    return runner


def test_engine_judge_integration():
    mock_gemini = MagicMock()
    mock_gemini.generate_evaluation.return_value = JUDGE_OUTPUT
    engine = EvaluationEngine(judge=LLMJudge(mock_gemini))

    report = engine.evaluate(
        finished_runner(),
        VerificationCriteria(final_states={"ORD-12345": ["PENDING"]}),
        BACKEND,
        BACKEND,
    )

    assert report.verdict.status == "PASS"
    assert isinstance(report.quality, EvaluationResult)
    assert report.quality.reasoning == JUDGE_OUTPUT["reasoning"]
    assert report.quality.scenario_id == 1
    assert report.judge_error is None
    mock_gemini.generate_evaluation.assert_called_once()


def test_engine_passes_conversation_to_judge():
    mock_judge = MagicMock()
    expected_quality = EvaluationResult(
        scenario_id=1,
        quality_scores=JUDGE_OUTPUT["quality_scores"],
        reasoning="The agent understood the request.",
    )
    mock_judge.evaluate.return_value = expected_quality
    runner = finished_runner()

    report = EvaluationEngine(judge=mock_judge).evaluate(
        runner, VerificationCriteria(), BACKEND, BACKEND
    )

    assert report.quality is expected_quality
    mock_judge.evaluate.assert_called_once_with(
        runner.scenario,
        runner.conversation_history
    )


def test_engine_verdict_ignores_judge_failure_reasons():
    mock_judge = MagicMock()
    mock_judge.evaluate.return_value = EvaluationResult(
        scenario_id=1,
        quality_scores={"relevance": 1, "coherence": 1, "helpfulness": 1, "repetition": 1},
        failure_reasons=["The agent did not verify anything."],
    )

    report = EvaluationEngine(judge=mock_judge).evaluate(
        finished_runner(),
        VerificationCriteria(final_states={"ORD-12345": ["PENDING"]}),
        BACKEND,
        BACKEND,
    )

    assert report.verdict.status == "PASS"
    assert report.quality.failure_reasons == ["The agent did not verify anything."]


def test_engine_judge_failure_keeps_verdict():
    mock_judge = MagicMock()
    mock_judge.evaluate.side_effect = RuntimeError("Gemini API unavailable")
    runner = finished_runner()

    report = EvaluationEngine(judge=mock_judge).evaluate(
        runner,
        VerificationCriteria(final_states={"ORD-12345": ["CANCELLED"]}),
        BACKEND,
        BACKEND,
    )

    assert report.verdict.status == "FAIL"
    assert report.quality is None
    assert "Gemini API unavailable" in report.judge_error
    assert runner.status == "COMPLETED"


def test_engine_without_judge():
    report = EvaluationEngine().evaluate(
        finished_runner(), VerificationCriteria(), BACKEND, BACKEND
    )
    assert report.quality is None
    assert report.judge_error is None


def test_engine_running():
    mock_judge = MagicMock()
    scenario = TestScenario(
        1, "order cancellation", "cancel an order",
        {}, "Order cancelled", 5
    )
    runner = SimulationRunner(scenario)
    runner.start_simulation()
    engine = EvaluationEngine(judge=mock_judge)
    with pytest.raises(ValueError):
        engine.evaluate(runner, VerificationCriteria(), BACKEND, BACKEND)
    mock_judge.evaluate.assert_not_called()
