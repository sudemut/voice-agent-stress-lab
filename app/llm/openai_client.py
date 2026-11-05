from app.llm.client import LLMClient
from openai import OpenAI


class OpenAIClient(LLMClient):
    def __init__(self, model_name,api_key):
        super().__init__(model_name)
        self.api_key=api_key
        self.client=OpenAI(api_key=api_key)

    def generate(self,system_prompt,conversation_history):
        response=self.client.responses.create(
                model=self.model_name,
                instructions=system_prompt,
                input=conversation_history)

        return response.output_text