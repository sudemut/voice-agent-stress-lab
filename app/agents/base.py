from app.models.agent_result import AgentResult


class BaseAgent:
    def __init__(self,name,system_prompt,llm_client):
        self.name=name
        self.system_prompt=system_prompt
        self.llm_client=llm_client

    def generate_response(self, conversation_history):
        data = self.llm_client.generate_structured(
            self.system_prompt,
            conversation_history
        )

        return AgentResult(
            message=data["message"],
            end_conversation=data["end_conversation"]
        )