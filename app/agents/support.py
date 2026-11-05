from app.agents.base import BaseAgent
from app.models.agent_result import AgentResult

class SupportAgent(BaseAgent):
    def __init__(self, name, system_prompt, llm_client, tool_service=None, tools=None):
        super().__init__(name, system_prompt, llm_client)
        self.tool_service=tool_service
        self.tools=tools

    
    def generate_response(self, conversation_history):
        if self.tool_service is None:
            return super().generate_response(conversation_history)
        result = self.tool_service.run(
            system_prompt=self.system_prompt,
            conversation_history=conversation_history,
            tools=self.tools
        )

        return AgentResult(
            message=result["content"],
            end_conversation=False,
            tool_calls=result["tool_calls"]
        )