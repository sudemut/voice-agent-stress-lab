"""Scripted stand-ins for GeminiClient so simulations run without any API."""
from types import SimpleNamespace


def tool_call(name, **arguments):
    return SimpleNamespace(
        function_calls=[SimpleNamespace(name=name, args=arguments)],
        text=None,
        candidates=[SimpleNamespace(content=f"<model requests {name}>")],
    )


def text(message):
    return SimpleNamespace(function_calls=None, text=message, candidates=[])


class ScriptedCustomerLLM:
    """Plays the customer: returns the scripted messages in order."""

    def __init__(self, messages, end_after_last=True):
        self.messages = list(messages)
        self.end_after_last = end_after_last

    def generate_structured(self, system_prompt, conversation_history):
        message = self.messages.pop(0)
        return {
            "message": message,
            "end_conversation": self.end_after_last and not self.messages,
        }


class ScriptedSupportLLM:
    """Plays the support agent: returns scripted Gemini-like responses.

    Items may be responses from tool_call()/text(), or an Exception
    instance to simulate the API failing at that point.
    """

    def __init__(self, responses):
        self.responses = list(responses)

    def _prepare_history(self, conversation_history):
        return list(conversation_history)

    def generate_next_with_tools(self, system_prompt, gemini_history, tools):
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response
