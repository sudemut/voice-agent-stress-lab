
import httpx
from google.genai import types

from app.tools.order_api_client import OrderAPIError


class ToolStepLimitExceeded(RuntimeError):
    """The agent kept requesting tools past max_tool_steps.

    This is agent behaviour (a tool loop), not an infrastructure failure,
    so the verifier counts it as FAIL rather than ERROR.
    """


class ToolCallingService:
    def __init__(
        self,
        gemini_client,
        tool_executer,
        max_tool_steps=5
    ):
        if (
            not isinstance(max_tool_steps, int)
            or isinstance(max_tool_steps, bool)
            or max_tool_steps < 1
        ):
            raise ValueError("max_tool_steps must be a positive integer")

        self.gemini_client = gemini_client
        self.tool_executer = tool_executer
        self.max_tool_steps = max_tool_steps

    def run(self, system_prompt, conversation_history, tools):


        gemini_history = self.gemini_client._prepare_history(
            conversation_history
        )

        tool_call_history = []

        response = self.gemini_client.generate_next_with_tools(
            system_prompt=system_prompt,
            gemini_history=gemini_history,
            tools=tools
        )

        for step in range(self.max_tool_steps + 1):

            function_calls = response.function_calls or []

            if not function_calls:
                if not response.text:
                    raise ValueError(
                        "Gemini returned an empty final response"
                    )

                return {
                    "type": "message",
                    "content": response.text,
                    "tool_calls": tool_call_history
                }

            if step >= self.max_tool_steps:
                raise ToolStepLimitExceeded(
                    f"Maximum tool steps exceeded: "
                    f"{self.max_tool_steps}"
                )

            if len(function_calls) != 1:
                raise ValueError(
                    "Parallel function calls are not supported yet"
                )

            function_call = function_calls[0]

            tool_name = function_call.name
            arguments = dict(function_call.args or {})

            try:
                tool_result = self.tool_executer.execute(
                    tool_name,
                    arguments
                )

                tool_response = {
                    "success": True,
                    "result": tool_result
                }

            except OrderAPIError as error:
                tool_response = {
                    "success": False,
                    "error": str(error),
                    "status_code": error.status_code
                }

            except (
                httpx.RequestError,
                ValueError,
                KeyError,
                TypeError
            ) as error:
                tool_response = {
                    "success": False,
                    "error": str(error)
                }


            tool_call_history.append({
                "name": tool_name,
                "arguments": arguments,
                "response": tool_response
            })


            model_content = response.candidates[0].content

            if model_content is None:
                raise ValueError(
                    "Gemini returned no model content"
                )

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
            response = self.gemini_client.generate_next_with_tools(
                system_prompt=system_prompt,
                gemini_history=gemini_history,
                tools=tools
            )

        raise RuntimeError("Tool calling loop ended unexpectedly")
