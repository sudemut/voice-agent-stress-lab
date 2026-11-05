from app.agents.base import BaseAgent
class CustomerAgent(BaseAgent):
    def __init__(self,name, system_prompt, llm_client,scenario):
        super().__init__(name,system_prompt,llm_client)
        self.scenario=scenario

