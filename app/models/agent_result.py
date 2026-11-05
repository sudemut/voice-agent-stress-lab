class AgentResult:
    def __init__(self,message,end_conversation,tool_calls=None):
        if not isinstance(message, str) or not message.strip():
            raise ValueError("Message must be a non-empty string")

        if not isinstance(end_conversation, bool):
            raise ValueError("end_conversation must be a boolean")

        if tool_calls is None:
            tool_calls = []
        
        if not isinstance(tool_calls,list):
            raise ValueError("It should be a list")
        self.message=message
        self.end_conversation=end_conversation
        self.tool_calls=tool_calls