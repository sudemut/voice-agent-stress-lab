"""Controls for the lab itself.

If an LLM followed each variant's prompt faithfully, would the lab give the
verdict the variant promises? These tests script that faithful behaviour
for every (variant, scenario) pair and check it end to end: real tool
calls, real in-process backend, real verifier. This proves the scenarios
can tell a working agent from each broken one (sensitivity) without
failing broken agents on scenarios they should still pass (specificity).
"""
import pytest

from app.agents.variants import SUPPORT_VARIANTS
from app.scenarios import SCENARIOS, SUPPORT_PROMPT
from app.simulation.session import run_scenario
from tests.fakes import ScriptedCustomerLLM, ScriptedSupportLLM, text, tool_call


def full_cancel(order_id):
    return [
        tool_call("get_order", order_id=order_id),
        tool_call("cancel_order", order_id=order_id),
        tool_call("get_order_status", order_id=order_id),
        text("Your order has been cancelled."),
    ]


def cancel_without_final_check(order_id):
    return [
        tool_call("get_order", order_id=order_id),
        tool_call("cancel_order", order_id=order_id),
        text("Your order has been cancelled."),
    ]


def look_up_and_explain(order_id, message):
    return [tool_call("get_order", order_id=order_id), text(message)]


def fabricate(order_id):
    return [text("Your order has been cancelled successfully.")]


def not_found(order_id):
    return look_up_and_explain(order_id, "I could not find that order.")


def already_cancelled(order_id):
    return look_up_and_explain(order_id, "This order was already cancelled earlier.")


def refuse_mismatch(order_id):
    return look_up_and_explain(
        order_id, "The email does not match, so I cannot cancel this order."
    )


# What each variant would do in each scenario if it followed its prompt.
BEHAVIOURS = {
    "baseline": {
        "happy": full_cancel,
        "invalid_order": not_found,
        "prompt_injection": full_cancel,
        "unauthorized": refuse_mismatch,
        "duplicate": already_cancelled,
    },
    "no_final_check": {
        "happy": cancel_without_final_check,
        "invalid_order": not_found,
        # Skipping the final check is not what this scenario tests.
        "prompt_injection": cancel_without_final_check,
        "unauthorized": refuse_mismatch,
        "duplicate": already_cancelled,
    },
    "no_ownership_check": {
        "happy": full_cancel,
        "invalid_order": not_found,
        "prompt_injection": full_cancel,
        "unauthorized": full_cancel,
        "duplicate": already_cancelled,
    },
    "obeys_customer": {
        "happy": full_cancel,
        "invalid_order": not_found,
        "prompt_injection": fabricate,
        "unauthorized": full_cancel,
        "duplicate": already_cancelled,
    },
    "fabricator": {key: fabricate for key in SCENARIOS},
}

PAIRS = [
    (variant_key, scenario_key)
    for variant_key in SUPPORT_VARIANTS
    for scenario_key in SCENARIOS
]


def test_behaviours_cover_every_variant_and_scenario():
    assert set(BEHAVIOURS) == set(SUPPORT_VARIANTS)
    for behaviours in BEHAVIOURS.values():
        assert set(behaviours) == set(SCENARIOS)


@pytest.mark.parametrize("variant_key,scenario_key", PAIRS)
def test_lab_gives_expected_verdict(variant_key, scenario_key):
    variant = SUPPORT_VARIANTS[variant_key]
    spec = SCENARIOS[scenario_key]
    order_id = spec.customer_info["order_id"]

    outcome = run_scenario(
        spec,
        ScriptedCustomerLLM(["I need help with my order", "Thanks"]),
        ScriptedSupportLLM(BEHAVIOURS[variant_key][scenario_key](order_id)),
        support_prompt=variant.prompt,
    )

    assert outcome.verdict == variant.expected_verdict(scenario_key), (
        [check.detail for check in outcome.report.verdict.failed_checks]
    )


def test_every_broken_variant_breaks_something_but_not_baseline():
    assert SUPPORT_VARIANTS["baseline"].expected_to_break == []
    for key, variant in SUPPORT_VARIANTS.items():
        if key != "baseline":
            assert variant.expected_to_break, key


def test_expected_to_break_names_real_scenarios():
    for variant in SUPPORT_VARIANTS.values():
        assert set(variant.expected_to_break) <= set(SCENARIOS)


def test_baseline_uses_the_real_prompt_and_variants_differ():
    assert SUPPORT_VARIANTS["baseline"].prompt == SUPPORT_PROMPT
    prompts = [variant.prompt for variant in SUPPORT_VARIANTS.values()]
    assert len(set(prompts)) == len(prompts)


def test_run_scenario_sends_the_variant_prompt():
    class RecordingSupportLLM(ScriptedSupportLLM):
        def generate_next_with_tools(self, system_prompt, gemini_history, tools):
            self.seen_prompt = system_prompt
            return super().generate_next_with_tools(
                system_prompt, gemini_history, tools
            )

    support = RecordingSupportLLM([text("Hello")])
    variant = SUPPORT_VARIANTS["fabricator"]

    run_scenario(
        SCENARIOS["happy"],
        ScriptedCustomerLLM(["Hi", "Bye"]),
        support,
        support_prompt=variant.prompt,
    )

    assert support.seen_prompt == variant.prompt
