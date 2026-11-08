import pytest

from app.evaluation.stats import wilson_interval
from app.scenarios import SCENARIOS
from app.simulation.batch import (
    ScenarioSummary,
    format_summary_table,
    run_batch,
    summarize_records,
)
from app.simulation.session import run_scenario
from tests.fakes import ScriptedCustomerLLM, ScriptedSupportLLM, text, tool_call


class FakeOutcome:
    def __init__(self, status, failed=(), error=None, quality=None):
        self.record = {
            "scenario": "happy",
            "verdict": {
                "status": status,
                "error": error,
                "checks": [
                    {"name": name, "passed": False, "detail": "", "safety": False}
                    for name in failed
                ],
            },
            "quality": quality,
        }

    def to_dict(self):
        return dict(self.record)


def scripted(outcomes):
    queue = list(outcomes)

    def run_once(spec):
        item = queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    return run_once


# --- wilson_interval --------------------------------------------------------

def test_wilson_known_value():
    low, high = wilson_interval(15, 20)
    assert low == pytest.approx(0.5313, abs=1e-3)
    assert high == pytest.approx(0.8881, abs=1e-3)


def test_wilson_all_pass_is_not_100_percent_certain():
    low, high = wilson_interval(20, 20)
    assert high == pytest.approx(1.0)
    assert low == pytest.approx(0.8389, abs=1e-3)


def test_wilson_zero_successes_stays_in_range():
    low, high = wilson_interval(0, 20)
    assert low == pytest.approx(0.0)
    assert 0 < high < 0.2


def test_wilson_no_trials():
    assert wilson_interval(0, 0) is None


def test_wilson_rejects_impossible_counts():
    with pytest.raises(ValueError):
        wilson_interval(5, 3)


# --- run_batch --------------------------------------------------------------

def test_batch_counts_pass_fail_error_separately():
    spec = SCENARIOS["happy"]
    run_once = scripted([
        FakeOutcome("PASS"),
        FakeOutcome("PASS"),
        FakeOutcome("FAIL", failed=["final_states"]),
        FakeOutcome("ERROR", error="ServerError: 503 UNAVAILABLE"),
    ])

    summaries, records = run_batch([spec], 4, run_once)
    summary = summaries[0]

    assert (summary.passed, summary.failed, summary.errored) == (2, 1, 1)
    assert summary.runs == 4
    assert [record["run"] for record in records] == [1, 2, 3, 4]
    assert summary.failed_checks == {"final_states": 1}
    assert summary.error_types == {"ServerError": 1}


def test_errors_are_excluded_from_pass_rate():
    spec = SCENARIOS["happy"]
    run_once = scripted(
        [FakeOutcome("PASS")] * 3
        + [FakeOutcome("ERROR", error="ServerError: down")] * 7
    )

    summaries, _ = run_batch([spec], 10, run_once)

    assert summaries[0].pass_rate == 1.0
    assert summaries[0].confidence_interval == wilson_interval(3, 3)


def test_crash_outside_orchestrator_counts_as_error():
    spec = SCENARIOS["happy"]
    run_once = scripted([ConnectionError("no network"), FakeOutcome("PASS")])

    summaries, records = run_batch([spec], 2, run_once)

    assert summaries[0].errored == 1
    assert summaries[0].passed == 1
    assert "ConnectionError" in records[0]["verdict"]["error"]


def test_agent_fault_fail_without_failed_checks_is_named():
    spec = SCENARIOS["happy"]
    run_once = scripted([
        FakeOutcome("FAIL", error="ToolStepLimitExceeded: Maximum tool steps"),
    ])
    summaries, _ = run_batch([spec], 1, run_once)
    assert summaries[0].failed_checks == {"ToolStepLimitExceeded": 1}


def test_batch_averages_judge_quality():
    spec = SCENARIOS["happy"]
    scores = {"relevance": 4, "coherence": 5, "helpfulness": 3, "repetition": 5}
    run_once = scripted([
        FakeOutcome("PASS", quality={"quality_scores": scores}),
        FakeOutcome("PASS", quality={"quality_scores": {**scores, "relevance": 2}}),
    ])
    summaries, _ = run_batch([spec], 2, run_once)
    assert summaries[0].mean_quality["relevance"] == 3.0


def test_batch_rejects_zero_runs():
    with pytest.raises(ValueError):
        run_batch([SCENARIOS["happy"]], 0, scripted([]))


def test_batch_runs_every_scenario_with_fresh_backends():
    """Real sessions: the same cancel-everything agent across scenarios."""
    def cancel_everything_agent(spec):
        order_id = spec.customer_info["order_id"]
        customer = ScriptedCustomerLLM(["Please cancel my order", "Thanks"])
        support = ScriptedSupportLLM([
            tool_call("get_order", order_id=order_id),
            tool_call("cancel_order", order_id=order_id),
            tool_call("get_order_status", order_id=order_id),
            text("Your order has been cancelled."),
        ])
        return run_scenario(spec, customer, support)

    specs = [SCENARIOS["happy"], SCENARIOS["unauthorized"]]
    summaries, _ = run_batch(specs, 3, cancel_everything_agent)
    by_key = {summary.key: summary for summary in summaries}

    # If state leaked, runs 2-3 of "happy" would start CANCELLED and fail.
    assert by_key["happy"].passed == 3
    assert by_key["unauthorized"].failed == 3


def test_summary_table_shows_rates_and_intervals():
    summary = ScenarioSummary(key="happy", passed=15, failed=5, errored=2)
    table = format_summary_table([summary])

    assert "| happy" in table
    assert "75%" in table
    assert "53% - 89%" in table
    assert "ERROR runs" in table


def test_ctrl_c_keeps_finished_runs():
    spec = SCENARIOS["happy"]
    run_once = scripted([FakeOutcome("PASS"), FakeOutcome("PASS"), KeyboardInterrupt()])

    summaries, records = run_batch([spec], 20, run_once)

    assert len(records) == 2
    assert summaries[0].passed == 2


def test_summarize_records_matches_batch_summary():
    spec = SCENARIOS["happy"]
    run_once = scripted([
        FakeOutcome("PASS"),
        FakeOutcome("FAIL", failed=["final_states"]),
        FakeOutcome("ERROR", error="ServerError: 503"),
    ])
    summaries, records = run_batch([spec], 3, run_once)

    rebuilt = summarize_records(records)

    assert rebuilt[0].to_dict() == summaries[0].to_dict()


def test_batch_labels_records_and_summaries_with_agent():
    spec = SCENARIOS["happy"]
    summaries, records = run_batch(
        [spec], 2, scripted([FakeOutcome("PASS"), FakeOutcome("FAIL")]),
        agent="fabricator",
    )
    assert summaries[0].agent == "fabricator"
    assert {record["agent"] for record in records} == {"fabricator"}


def test_summarize_records_separates_agents():
    records = [
        {**FakeOutcome("PASS").to_dict(), "agent": "baseline"},
        {**FakeOutcome("FAIL").to_dict(), "agent": "fabricator"},
        {**FakeOutcome("FAIL").to_dict(), "agent": "fabricator"},
    ]
    summaries = summarize_records(records)
    by_agent = {summary.agent: summary for summary in summaries}
    assert (by_agent["baseline"].passed, by_agent["fabricator"].failed) == (1, 2)


def test_table_shows_agent_and_expected_columns():
    summaries = [
        ScenarioSummary(key="happy", agent="baseline", passed=20),
        ScenarioSummary(key="happy", agent="no_final_check", failed=20),
    ]
    table = format_summary_table(
        summaries,
        expected=lambda agent, key: "PASS" if agent == "baseline" else "FAIL",
    )
    assert "| Agent" in table and "Expected" in table
    assert "| no_final_check | happy" in table
    assert "no_final_check/happy FAIL reasons" not in table  # no checks recorded


def test_table_hides_agent_column_for_baseline_only():
    table = format_summary_table([ScenarioSummary(key="happy", passed=1)])
    assert "Agent" not in table
    assert "Expected" not in table
