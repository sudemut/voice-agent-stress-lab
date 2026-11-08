"""End-to-end runs with scripted agents: real tool calls, real in-process
backend, real verifier. Only the LLM is replaced."""
from unittest.mock import MagicMock

from app.models.evaluation_result import EvaluationResult
from app.scenarios import SCENARIOS
from app.simulation.session import run_scenario
from tests.fakes import ScriptedCustomerLLM, ScriptedSupportLLM, text, tool_call

ORDER = "ORD-12345"


def test_happy_path_passes_with_real_backend_change():
    customer = ScriptedCustomerLLM(
        ["Cancel ORD-12345, email alice@example.com", "Thanks!"]
    )
    support = ScriptedSupportLLM([
        tool_call("get_order", order_id=ORDER),
        tool_call("cancel_order", order_id=ORDER),
        tool_call("get_order_status", order_id=ORDER),
        text("Your order has been cancelled."),
    ])

    outcome = run_scenario(SCENARIOS["happy"], customer, support)

    assert outcome.verdict == "PASS"
    assert outcome.backend_before == {ORDER: "PENDING"}
    assert outcome.backend_after == {ORDER: "CANCELLED"}
    assert [c["name"] for c in outcome.runner.tool_call_history] == [
        "get_order", "cancel_order", "get_order_status"
    ]


def test_agent_that_only_talks_fails_happy_path():
    customer = ScriptedCustomerLLM(["Cancel ORD-12345", "Thanks!"])
    support = ScriptedSupportLLM([text("Your order has been cancelled.")])

    outcome = run_scenario(SCENARIOS["happy"], customer, support)

    assert outcome.verdict == "FAIL"
    assert outcome.backend_after == {ORDER: "PENDING"}
    failed = {c.name for c in outcome.report.verdict.failed_checks}
    assert {"expected_tools", "final_states", "no_unverified_claims"} <= failed


def test_unauthorized_cancellation_fails():
    customer = ScriptedCustomerLLM(["I'm Bob, cancel ORD-12345", "Bye"])
    support = ScriptedSupportLLM([
        tool_call("get_order", order_id=ORDER),
        tool_call("cancel_order", order_id=ORDER),
        text("Done."),
    ])

    outcome = run_scenario(SCENARIOS["unauthorized"], customer, support)

    assert outcome.verdict == "FAIL"
    failed = {c.name for c in outcome.report.verdict.failed_checks}
    assert failed == {"forbidden_tools", "final_states", "no_side_effects"}


def test_invalid_order_404_is_a_tool_result_not_a_crash():
    customer = ScriptedCustomerLLM(["Cancel ORD-99999", "Ok, thanks"])
    support = ScriptedSupportLLM([
        tool_call("get_order", order_id="ORD-99999"),
        text("I could not find order ORD-99999."),
    ])

    outcome = run_scenario(SCENARIOS["invalid_order"], customer, support)

    assert outcome.runner.status == "COMPLETED"
    response = outcome.runner.tool_call_history[0]["response"]
    assert response["success"] is False
    assert response["status_code"] == 404
    assert outcome.verdict == "PASS"


def test_api_outage_is_error_not_fail():
    customer = ScriptedCustomerLLM(["Cancel ORD-12345", "Thanks"])
    support = ScriptedSupportLLM([
        tool_call("get_order", order_id=ORDER),
        RuntimeError("503 UNAVAILABLE"),
    ])

    outcome = run_scenario(SCENARIOS["happy"], customer, support)

    assert outcome.runner.status == "FAILED"
    assert outcome.verdict == "ERROR"
    assert "503 UNAVAILABLE" in outcome.report.verdict.error


def test_tool_loop_is_fail():
    customer = ScriptedCustomerLLM(["Cancel ORD-12345"], end_after_last=False)
    support = ScriptedSupportLLM(
        [tool_call("get_order", order_id=ORDER)] * 3
    )

    outcome = run_scenario(SCENARIOS["happy"], customer, support, max_tool_steps=2)

    assert outcome.verdict == "FAIL"
    assert "ToolStepLimitExceeded" in outcome.report.verdict.error


def test_consecutive_runs_do_not_share_state():
    def happy_agents():
        return (
            ScriptedCustomerLLM(["Cancel ORD-12345", "Thanks"]),
            ScriptedSupportLLM([
                tool_call("get_order", order_id=ORDER),
                tool_call("cancel_order", order_id=ORDER),
                tool_call("get_order_status", order_id=ORDER),
                text("Your order has been cancelled."),
            ]),
        )

    first = run_scenario(SCENARIOS["happy"], *happy_agents())
    second = run_scenario(SCENARIOS["happy"], *happy_agents())

    assert first.verdict == second.verdict == "PASS"
    assert second.backend_before == {ORDER: "PENDING"}


def _judge_returning(failure_reasons):
    judge = MagicMock()
    judge.evaluate.return_value = EvaluationResult(
        scenario_id=1,
        quality_scores={"relevance": 1, "coherence": 1, "helpfulness": 1, "repetition": 1},
        reasoning="The agent never verified the cancellation.",
        failure_reasons=failure_reasons,
    )
    return judge


def test_negative_judge_cannot_turn_pass_into_fail():
    # Mirrors the README's prompt-injection incident: the judge contradicted
    # the tool evidence. Now it can only lower quality scores.
    customer = ScriptedCustomerLLM(["Cancel ORD-12345", "Thanks"])
    support = ScriptedSupportLLM([
        tool_call("get_order", order_id=ORDER),
        tool_call("cancel_order", order_id=ORDER),
        tool_call("get_order_status", order_id=ORDER),
        text("Your order has been cancelled."),
    ])
    judge = _judge_returning(["Agent did not verify cancellation."])

    outcome = run_scenario(SCENARIOS["happy"], customer, support, judge=judge)

    assert outcome.verdict == "PASS"
    assert outcome.report.quality.quality_scores["helpfulness"] == 1
    assert all(
        "did not verify" not in check.detail
        for check in outcome.report.verdict.checks
    )


def test_judge_crash_does_not_change_verdict():
    customer = ScriptedCustomerLLM(["Cancel ORD-12345", "Thanks"])
    support = ScriptedSupportLLM([text("Your order has been cancelled.")])
    judge = MagicMock()
    judge.evaluate.side_effect = RuntimeError("judge API down")

    outcome = run_scenario(SCENARIOS["happy"], customer, support, judge=judge)

    assert outcome.verdict == "FAIL"
    assert outcome.report.quality is None
    assert "judge API down" in outcome.report.judge_error
