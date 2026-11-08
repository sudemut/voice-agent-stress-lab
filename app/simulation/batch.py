import time
from collections import Counter
from dataclasses import dataclass, field

from app.evaluation.stats import wilson_interval
from app.evaluation.verifier import ERROR, FAIL, PASS


@dataclass
class ScenarioSummary:
    """Aggregated results for one scenario across N runs.

    ERROR runs (infrastructure failed, e.g. the LLM API was down) are
    reported separately and excluded from the pass rate, because they say
    nothing about the agent. pass_rate = PASS / (PASS + FAIL).
    """

    key: str
    agent: str = "baseline"
    passed: int = 0
    failed: int = 0
    errored: int = 0
    failed_checks: Counter = field(default_factory=Counter)
    error_types: Counter = field(default_factory=Counter)
    quality_totals: Counter = field(default_factory=Counter)
    quality_count: int = 0

    @property
    def runs(self):
        return self.passed + self.failed + self.errored

    @property
    def decided(self):
        return self.passed + self.failed

    @property
    def pass_rate(self):
        return self.passed / self.decided if self.decided else None

    @property
    def confidence_interval(self):
        return wilson_interval(self.passed, self.decided)

    @property
    def mean_quality(self):
        if not self.quality_count:
            return None
        return {
            metric: total / self.quality_count
            for metric, total in self.quality_totals.items()
        }

    def add(self, record):
        status = record["verdict"]["status"]
        if status == PASS:
            self.passed += 1
        elif status == FAIL:
            self.failed += 1
            failed_names = [
                check["name"]
                for check in record["verdict"]["checks"]
                if not check["passed"]
            ]
            # A FAIL with no failed check is an agent-caused crash
            # (e.g. a tool loop), so name it after the error type.
            if not failed_names and record["verdict"]["error"]:
                failed_names = [record["verdict"]["error"].split(":", 1)[0]]
            self.failed_checks.update(failed_names)
        elif status == ERROR:
            self.errored += 1
            error = record["verdict"]["error"] or "unknown"
            self.error_types[error.split(":", 1)[0]] += 1
        else:
            raise ValueError(f"Unknown verdict status: {status}")

        quality = record.get("quality")
        if quality and quality.get("quality_scores"):
            self.quality_count += 1
            self.quality_totals.update(quality["quality_scores"])

    def to_dict(self):
        interval = self.confidence_interval
        return {
            "agent": self.agent,
            "scenario": self.key,
            "runs": self.runs,
            "pass": self.passed,
            "fail": self.failed,
            "error": self.errored,
            "pass_rate": self.pass_rate,
            "ci95": list(interval) if interval else None,
            "failed_checks": dict(self.failed_checks),
            "error_types": dict(self.error_types),
            "mean_quality": self.mean_quality,
        }


def _crash_record(spec, error):
    """A run that blew up outside the orchestrator still counts, as ERROR."""
    return {
        "scenario": spec.key,
        "verdict": {
            "status": ERROR,
            "error": f"{type(error).__name__}: {error}",
            "checks": [],
        },
        "quality": None,
        "judge_error": None,
    }


def run_batch(
    specs,
    runs,
    run_once,
    delay_seconds=0,
    on_result=None,
    agent="baseline",
):
    """Run every spec `runs` times; each run gets a fresh backend.

    run_once(spec) -> RunOutcome is injected so tests can use fake agents.
    Returns (summaries, records) where records holds one dict per run.

    Ctrl+C stops the batch cleanly: the run in progress is discarded and
    the finished runs are returned, so partial results are not lost.
    """
    if runs < 1:
        raise ValueError("runs must be at least 1")

    summaries = {
        spec.key: ScenarioSummary(key=spec.key, agent=agent) for spec in specs
    }
    records = []

    try:
        for spec in specs:
            for index in range(1, runs + 1):
                try:
                    record = run_once(spec).to_dict()
                except Exception as error:
                    record = _crash_record(spec, error)
                record["run"] = index
                record["agent"] = agent

                summaries[spec.key].add(record)
                records.append(record)
                if on_result is not None:
                    on_result(spec, index, record)
                if delay_seconds:
                    time.sleep(delay_seconds)
    except KeyboardInterrupt:
        pass

    return list(summaries.values()), records


def summarize_records(records):
    """Rebuild per-(agent, scenario) summaries from saved run records."""
    summaries = {}
    for record in records:
        agent = record.get("agent", "baseline")
        key = (agent, record["scenario"])
        if key not in summaries:
            summaries[key] = ScenarioSummary(key=record["scenario"], agent=agent)
        summaries[key].add(record)
    return list(summaries.values())


def _percent(value):
    return "-" if value is None else f"{value * 100:.0f}%"


def format_summary_table(summaries, expected=None):
    """expected(agent, scenario) -> "PASS"/"FAIL" adds an Expected column."""
    show_agent = any(summary.agent != "baseline" for summary in summaries)
    headers = ["Scenario", "Runs", "PASS", "FAIL", "ERROR", "Pass rate", "95% CI"]
    if expected is not None:
        headers.insert(1, "Expected")
    if show_agent:
        headers.insert(0, "Agent")

    def label(summary):
        return f"{summary.agent}/{summary.key}" if show_agent else summary.key

    rows = []
    for summary in summaries:
        interval = summary.confidence_interval
        row = [
            summary.key,
            str(summary.runs),
            str(summary.passed),
            str(summary.failed),
            str(summary.errored),
            _percent(summary.pass_rate),
            (
                f"{_percent(interval[0])} - {_percent(interval[1])}"
                if interval else "-"
            ),
        ]
        if expected is not None:
            row.insert(1, expected(summary.agent, summary.key))
        if show_agent:
            row.insert(0, summary.agent)
        rows.append(row)

    widths = [
        max(len(headers[column]), *(len(row[column]) for row in rows))
        for column in range(len(headers))
    ]

    def line(cells):
        return "| " + " | ".join(
            cell.ljust(width) for cell, width in zip(cells, widths)
        ) + " |"

    output = [
        line(headers),
        "|" + "|".join("-" * (width + 2) for width in widths) + "|",
    ]
    output.extend(line(row) for row in rows)

    notes = []
    for summary in summaries:
        if summary.failed_checks:
            notes.append(
                f"{label(summary)} FAIL reasons: {dict(summary.failed_checks)}"
            )
        if summary.error_types:
            notes.append(
                f"{label(summary)} ERROR types: {dict(summary.error_types)}"
            )
        if summary.mean_quality:
            scores = ", ".join(
                f"{metric}={value:.1f}"
                for metric, value in sorted(summary.mean_quality.items())
            )
            notes.append(f"{label(summary)} mean judge quality: {scores}")

    if notes:
        output.append("")
        output.extend(notes)
    output.append("")
    output.append(
        "Pass rate = PASS / (PASS + FAIL). ERROR runs (infrastructure "
        "failures) are excluded. CI = Wilson score interval."
    )
    if expected is not None:
        output.append(
            "Expected = the verdict a working lab should give. Broken control "
            "agents should FAIL their targeted scenarios and PASS the rest."
        )
    return "\n".join(output)
