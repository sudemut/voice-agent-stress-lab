from dataclasses import dataclass

from app.evaluation.verifier import RunEvidence, ScenarioVerifier


@dataclass
class EvaluationReport:
    """Verdict and quality are kept apart on purpose.

    verdict comes only from deterministic evidence checks. quality is the
    LLM judge's opinion of the conversation and never changes the verdict;
    if the judge fails, quality is None and judge_error explains why.
    """

    verdict: object
    quality: object = None
    judge_error: str = None

    def to_dict(self):
        return {
            "verdict": self.verdict.to_dict(),
            "quality": self.quality.to_dict() if self.quality else None,
            "judge_error": self.judge_error,
        }


class EvaluationEngine:
    def __init__(self, verifier=None, judge=None):
        self.verifier = verifier or ScenarioVerifier()
        self.judge = judge

    def evaluate(self, runner, criteria, backend_before, backend_after):
        if runner.status in ["PENDING", "RUNNING"]:
            raise ValueError(
                "To evaluate the process, it should be completed or failed"
            )

        if runner.status not in ["COMPLETED", "FAILED"]:
            raise ValueError(
                f"Invalid runner status: {runner.status}"
            )

        evidence = RunEvidence.from_runner(
            runner, backend_before, backend_after
        )
        verdict = self.verifier.verify(criteria, evidence)

        quality = None
        judge_error = None
        if self.judge is not None and runner.conversation_history:
            try:
                quality = self.judge.evaluate(
                    runner.scenario,
                    runner.conversation_history
                )
            except Exception as error:
                judge_error = f"{type(error).__name__}: {error}"

        return EvaluationReport(
            verdict=verdict,
            quality=quality,
            judge_error=judge_error,
        )
