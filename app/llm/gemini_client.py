
from app.llm.client import LLMClient
from google import genai
from google.genai import types
from app.models.agent_result import AgentResult
import json
from app.tools.declarations import order_tools


class GeminiClient(LLMClient):
    def __init__(self, model_name, api_key):
        super().__init__(model_name)
        self.api_key = api_key
        self.client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            timeout=30000,
            retry_options=types.HttpRetryOptions(
                attempts=5,
                initial_delay=2,
                max_delay=20
            )
        )
    )
    def _prepare_history(self, conversation_history):
        gemini_history = []

        for message in conversation_history:
            role = message["role"]

            if role == "assistant":
                role = "model"
            elif role != "user":
                raise ValueError(f"Invalid role: {role}")

            gemini_history.append(
                types.Content(
                    role=role,
                    parts=[
                        types.Part.from_text(
                            text=message["content"]
                        )
                    ]
                )
            )

        if not gemini_history:
            gemini_history.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text="Start the conversation according to your role and instructions."
                        )
                    ]
                )
            )

        return gemini_history


    def generate(self, system_prompt, conversation_history):
        gemini_history = []

        for message in conversation_history:
            role = message["role"]

            if role == "assistant":
                role = "model"
            elif role != "user":
                raise ValueError(f"Invalid role: {role}")

            gemini_history.append(
                types.Content(
                    role=role,
                    parts=[
                        types.Part.from_text(
                            text=message["content"]
                        )
                    ]
                )
            )
        if not gemini_history:
            gemini_history.append(
                    types.Content(
                    role="user",
            parts=[
                types.Part.from_text(
                    text="Start the conversation according to your role and instructions."
                )
            ]
        )
    )
        print("[DEBUG] generate() called:", self.model_name)

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=gemini_history,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt
            )
        )

        return response.text

    def generate_structured(self, system_prompt, conversation_history):

        gemini_history = self._prepare_history(conversation_history)
        print("[DEBUG] generate_structured() called:", self.model_name)

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=gemini_history,
            config=types.GenerateContentConfig(
                system_instruction=(
                    system_prompt
                    + "\nDecide whether the conversation should end. "
                      "Set end_conversation to true only when your role "
                      "is finished with the conversation or you intend "
                      "to end the interaction. "
                      "Do not claim that an external action succeeded "
                      "unless it was actually verified."
                ),
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "message": {
                            "type": "STRING"
                        },
                        "end_conversation": {
                            "type": "BOOLEAN"
                        }
                    },
                    "required": [
                        "message",
                        "end_conversation"
                    ]
                }
            )
        )

        if not response.text:
            raise ValueError("Gemini returned an empty structured response")

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as e:
            raise ValueError("Gemini returned invalid JSON") from e

        if not isinstance(data, dict):
            raise ValueError("Structured response must be an object")

        if "message" not in data or "end_conversation" not in data:
            raise ValueError("Missing required structured response fields")

        # AgentResult validates the actual values and types.
        result = AgentResult(
            message=data["message"],
            end_conversation=data["end_conversation"]
        )

        return {
            "message": result.message,
            "end_conversation": result.end_conversation
        }

    def generate_with_tools(self,system_prompt,conversation_history,tools):
        gemini_history = self._prepare_history(conversation_history)
        print("[DEBUG] generate_with_tools() called:", self.model_name)

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=gemini_history,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[tools]
            )
        )

        return response

    def generate_after_tool(
        self,
        system_prompt,
        conversation_history,
        tools,
        model_content,
        tool_name,
        tool_response
    ):
        gemini_history = self._prepare_history(conversation_history)


        gemini_history.append(model_content)


        function_response = types.Part.from_function_response(
            name=tool_name,
            response=tool_response
        )


        gemini_history.append(
            types.Content(
                role="user",
                parts=[function_response]
            )
        )
        print("[DEBUG] generate_after_tool() called:", self.model_name)


        response = self.client.models.generate_content(
            model=self.model_name,
            contents=gemini_history,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[tools]
            )
        )

        if response.function_calls:
            raise ValueError(
                "Gemini requested another tool call, "
                "but multiple tool calls are not supported yet."
            )

        if not response.text:
            raise ValueError("Gemini returned an empty final response")

        return response.text

        
    def generate_evaluation(self, evaluation_prompt):

        evaluation_schema = {
            "type": "object",
            "properties": {
                "quality_scores": {
                    "type": "object",
                    "properties": {
                        "relevance": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 5
                        },
                        "coherence": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 5
                        },
                        "helpfulness": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 5
                        },
                        "repetition": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 5
                        }
                    },
                    "required": [
                        "relevance",
                        "coherence",
                        "helpfulness",
                        "repetition"
                    ],
                    "additionalProperties": False
                },
                "reasoning": {
                    "type": "string"
                },
                "evidence": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "failure_reasons": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": [
                "quality_scores",
                "reasoning",
                "evidence",
                "failure_reasons"
            ],
            "additionalProperties": False
        }

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=evaluation_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=evaluation_schema
            )
        )

        if not response.text:
            raise ValueError("Gemini returned an empty evaluation")

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError as error:
            raise ValueError(
                "Gemini returned invalid evaluation JSON"
            ) from error

        if not isinstance(data, dict):
            raise ValueError("Evaluation must be a dictionary")

        required_fields = {
            "quality_scores",
            "reasoning",
            "evidence",
            "failure_reasons"
        }

        if not required_fields.issubset(data):
            raise ValueError("Evaluation response is missing required fields")

        return data
    def generate_next_with_tools(
        self,
        system_prompt,
        gemini_history,
        tools
    ):
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=gemini_history,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=[tools]
            )
        )

        return response