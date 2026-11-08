from dataclasses import dataclass

from app.agents.customer import CustomerAgent
from app.agents.support import SupportAgent
from app.evaluation.engine import EvaluationEngine
from app.scenarios import SUPPORT_PROMPT
from app.simulation.backend import InProcessBackend
from app.simulation.orchestrator import ConversationOrchestrator
from app.simulation.runner import SimulationRunner
from app.tools.declarations import order_tools
from app.tools.executor import ToolExecutor
from app.tools.tool_calling_service import ToolCallingService

MAX_TOOL_STEPS = 5


@dataclass
class RunOutcome:
    spec: object
    runner: SimulationRunner
    backend_before: dict
    backend_after: dict
    report: object

    @property
    def verdict(self):
        return self.report.verdict.status

    def to_dict(self):
        return {
            "scenario": self.spec.key,
            "simulation_status": self.runner.status,
            "termination_reason": self.runner.termination_reason,
            "turns": self.runner.current_turn,
            "backend_before": self.backend_before,
            "backend_after": self.backend_after,
            "conversation": self.runner.conversation_history,
            "tool_calls": self.runner.tool_call_history,
            **self.report.to_dict(),
        }


def run_scenario(
    spec,
    customer_llm,
    support_llm,
    judge=None,
    max_tool_steps=MAX_TOOL_STEPS,
    support_prompt=SUPPORT_PROMPT,
):
    """Run one scenario against its own freshly seeded in-process backend."""
    scenario = spec.to_test_scenario()

    with InProcessBackend(spec.initial_orders) as backend:
        tool_service = ToolCallingService(
            gemini_client=support_llm,
            tool_executer=ToolExecutor(backend.order_api_client),
            max_tool_steps=max_tool_steps,
        )
        customer = CustomerAgent(
            name="customer",
            system_prompt=spec.customer_prompt,
            llm_client=customer_llm,
            scenario=scenario,
        )
        support = SupportAgent(
            name="support",
            system_prompt=support_prompt,
            llm_client=support_llm,
            tool_service=tool_service,
            tools=order_tools,
        )
        runner = SimulationRunner(scenario)
        orchestrator = ConversationOrchestrator(
            customer_agent=customer,
            support_agent=support,
            runner=runner,
        )

        backend_before = backend.snapshot()
        orchestrator.run()
        backend_after = backend.snapshot()

    report = EvaluationEngine(judge=judge).evaluate(
        runner,
        spec.criteria,
        backend_before,
        backend_after,
    )
    return RunOutcome(
        spec=spec,
        runner=runner,
        backend_before=backend_before,
        backend_after=backend_after,
        report=report,
    )
