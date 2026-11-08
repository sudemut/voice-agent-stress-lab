
class EvaluationResult:
    """Conversation-quality scores from the LLM judge.

    Deliberately has no task-success field: whether the task succeeded is
    decided by ScenarioVerifier from tool and backend evidence.
    """

    REQUIRED_METRICS = {
        "relevance",
        "coherence",
        "helpfulness",
        "repetition"
    }

    def __init__(
        self,
        scenario_id,
        quality_scores=None,
        reasoning="",
        evidence=None,
        failure_reasons=None
    ):
        self.scenario_id = scenario_id

        # Validate quality scores
        if quality_scores is None:
            quality_scores = {}

        if not isinstance(quality_scores, dict):
            raise ValueError("quality_scores must be a dictionary")

        if quality_scores and set(quality_scores.keys()) != self.REQUIRED_METRICS:
            raise ValueError(
                "quality_scores must contain relevance, coherence, "
                "helpfulness and repetition"
            )

        for metric, score in quality_scores.items():
            if type(score) is not int or not 1 <= score <= 5:
                raise ValueError(
                    f"{metric} score must be an integer between 1 and 5"
                )

        self.quality_scores = quality_scores.copy()

        # Validate reasoning
        if not isinstance(reasoning, str):
            raise ValueError("reasoning must be a string")

        self.reasoning = reasoning

        # Validate evidence
        if evidence is None:
            evidence = []

        if not isinstance(evidence, list):
            raise ValueError("evidence must be a list")

        if not all(isinstance(item, str) for item in evidence):
            raise ValueError("All evidence items must be strings")

        self.evidence = evidence.copy()

        # Validate failure reasons
        if failure_reasons is None:
            failure_reasons = []

        if not isinstance(failure_reasons, list):
            raise ValueError("failure_reasons must be a list")

        if not all(isinstance(item, str) for item in failure_reasons):
            raise ValueError("All failure_reasons items must be strings")

        self.failure_reasons = failure_reasons.copy()

    def to_dict(self):
        return {
            "scenario_id": self.scenario_id,
            "quality_scores": self.quality_scores.copy(),
            "reasoning": self.reasoning,
            "evidence": self.evidence.copy(),
            "failure_reasons": self.failure_reasons.copy()
        }
