import argparse
import json
import os

from dotenv import load_dotenv

from app.agents.variants import SUPPORT_VARIANTS
from app.api.server import create_app
from app.evaluation.llm_judge import LLMJudge
from app.llm.gemini_client import GeminiClient
from app.scenarios import SCENARIOS
from app.simulation.batch import format_summary_table, run_batch, summarize_records
from app.simulation.session import run_scenario

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_RPM = float(os.getenv("GEMINI_RPM", "0")) or None

# Still available for manual exploration: python -m uvicorn app.main:app
# Simulations do not need it; they use an in-process backend per run.
app = create_app()


def print_outcome(outcome):
    runner = outcome.runner
    print("\n=== CONVERSATION HISTORY ===")
    for message in runner.conversation_history:
        print(f"{message['role'].upper()}: {message['content']}")

    print("\n=== TOOL CALL HISTORY ===")
    for call in runner.tool_call_history:
        print(f"[turn {call['turn']}] Tool:", call["name"])
        print("Arguments:", call["arguments"])
        print("Response:", call["response"])
        print("------------------------------")

    print("\n=== SIMULATION RESULT ===")
    print("Status:", runner.status, f"({runner.termination_reason})")
    print("Turns:", runner.current_turn)
    if runner.error is not None:
        print("Error:", type(runner.error).__name__, str(runner.error))
    print("Backend before:", outcome.backend_before)
    print("Backend after: ", outcome.backend_after)

    verdict = outcome.report.verdict
    print("\n=== VERDICT (deterministic) ===")
    for check in verdict.checks:
        mark = "ok  " if check.passed else "FAIL"
        print(f"  [{mark}] {check.name}: {check.detail}")
    print("Verdict:", verdict.status)

    print("\n=== CONVERSATION QUALITY (LLM judge, does not affect verdict) ===")
    if outcome.report.quality is not None:
        quality = outcome.report.quality
        print("Scores:", quality.quality_scores)
        print("Reasoning:", quality.reasoning)
        if quality.failure_reasons:
            print("Issues:", quality.failure_reasons)
    elif outcome.report.judge_error:
        print("Judge unavailable:", outcome.report.judge_error)
    else:
        print("Judge skipped.")


def print_progress(spec, index, record, agent="baseline"):
    status = record["verdict"]["status"]
    detail = ""
    if status == "FAIL":
        failed = [
            check["name"]
            for check in record["verdict"]["checks"]
            if not check["passed"]
        ]
        detail = f" {failed or record['verdict']['error']}"
    elif status == "ERROR":
        detail = f" {record['verdict']['error']}"
    label = spec.key if agent == "baseline" else f"{agent}/{spec.key}"
    print(f"  {label} run {index}: {status}{detail}", flush=True)


def main():
    parser = argparse.ArgumentParser(
        description="Run customer-support agent scenarios."
    )
    parser.add_argument(
        "--scenario",
        choices=[*SCENARIOS.keys(), "all"],
        default="happy",
    )
    parser.add_argument(
        "--agent",
        choices=[*SUPPORT_VARIANTS.keys(), "all"],
        default="baseline",
        help="Support agent to test. Variants other than baseline are "
             "deliberately broken controls for the lab itself.",
    )
    parser.add_argument(
        "--runs", type=int, default=1,
        help="Runs per scenario. More than 1 (or --scenario all) runs a batch.",
    )
    parser.add_argument(
        "--judge", action=argparse.BooleanOptionalAction, default=None,
        help="Score conversation quality with the LLM judge "
             "(default: on for a single run, off for batches).",
    )
    parser.add_argument(
        "--delay", type=float, default=0,
        help="Seconds to wait between batch runs (helps with rate limits).",
    )
    parser.add_argument(
        "--rpm", type=float, default=GEMINI_RPM,
        help="Max Gemini requests per minute across all agents "
             "(free tier: use 12). Default: GEMINI_RPM env var, else no limit.",
    )
    parser.add_argument(
        "--out", help="Write per-run records and the summary to this JSON file.",
    )
    args = parser.parse_args()

    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is missing")
    if args.runs < 1:
        parser.error("--runs must be at least 1")

    gemini_client = GeminiClient(
        model_name=GEMINI_MODEL,
        api_key=GEMINI_API_KEY,
        requests_per_minute=args.rpm,
    )
    specs = (
        list(SCENARIOS.values()) if args.scenario == "all"
        else [SCENARIOS[args.scenario]]
    )
    variants = (
        list(SUPPORT_VARIANTS.values()) if args.agent == "all"
        else [SUPPORT_VARIANTS[args.agent]]
    )
    is_batch = args.runs > 1 or len(specs) > 1 or len(variants) > 1
    use_judge = (not is_batch) if args.judge is None else args.judge
    judge = LLMJudge(gemini_client) if use_judge else None

    def run_with(variant):
        def run_once(spec):
            return run_scenario(
                spec,
                gemini_client,
                gemini_client,
                judge=judge,
                support_prompt=variant.prompt,
            )
        return run_once

    if not is_batch:
        spec = specs[0]
        variant = variants[0]
        print("\n================================")
        print("RUNNING TEST:", spec.name)
        print("AGENT:", variant.key, "-", variant.description)
        if variant.key != "baseline":
            print("EXPECTED VERDICT:", variant.expected_verdict(spec.key))
        print("================================")
        outcome = run_with(variant)(spec)
        print_outcome(outcome)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as file:
                json.dump(outcome.to_dict(), file, indent=2, default=str)
        return

    total_runs = args.runs * len(specs) * len(variants)
    show_expected = any(variant.key != "baseline" for variant in variants)
    completed = []

    def expected(agent, scenario_key):
        return SUPPORT_VARIANTS[agent].expected_verdict(scenario_key)

    def write_results(summaries):
        with open(args.out, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "model": GEMINI_MODEL,
                    "runs_per_scenario": args.runs,
                    "agents": {
                        variant.key: {
                            "description": variant.description,
                            "expected_to_break": variant.expected_to_break,
                        }
                        for variant in variants
                    },
                    "complete": len(completed) == total_runs,
                    "summary": [summary.to_dict() for summary in summaries],
                    "runs": completed,
                },
                file,
                indent=2,
                default=str,
            )

    def on_result(spec, index, record):
        print_progress(spec, index, record, agent=record["agent"])
        completed.append(record)
        # Save after every run so an interruption never loses finished runs.
        if args.out:
            write_results(summarize_records(completed))

    print(f"Running {len(variants)} agent(s) x {len(specs)} scenario(s) x "
          f"{args.runs} runs = {total_runs} runs "
          f"(judge {'on' if judge else 'off'}). Ctrl+C stops and keeps "
          "finished runs.")
    summaries = []
    for variant in variants:
        variant_summaries, records = run_batch(
            specs,
            args.runs,
            run_with(variant),
            delay_seconds=args.delay,
            on_result=on_result,
            agent=variant.key,
        )
        summaries.extend(variant_summaries)
        if len(records) < args.runs * len(specs):
            break  # Ctrl+C: do not start the next agent.

    if len(completed) < total_runs:
        print(f"\nInterrupted: {len(completed)} of {total_runs} runs finished.")
    print()
    print(format_summary_table(
        summaries, expected=expected if show_expected else None
    ))

    if args.out:
        print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
