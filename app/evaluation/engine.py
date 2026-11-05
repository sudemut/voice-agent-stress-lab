
class EvaluationEngine:
    def __init__(self, judge, task_verifier=None):
        self.judge = judge
        self.task_verifier = task_verifier

    def evaluate(self, runner):
        if runner.status in ["PENDING", "RUNNING"]:
            raise ValueError(
                "To evaluate the process, it should be completed or failed"
            )

        if runner.status not in ["COMPLETED", "FAILED"]:
            raise ValueError(
                f"Invalid runner status: {runner.status}"
            )

        result = self.judge.evaluate(
            runner.scenario,
            runner.conversation_history
        )
        if self.task_verifier is not None:
            task_status, evidence, failure_reasons = (
                self.task_verifier.verify(runner)
            )

            result.task_success = task_status

            result.evidence.extend(evidence)
            result.failure_reasons.extend(failure_reasons)

        return result
