class LLMClient():
    def __init__(self,model_name):
        self.model_name=model_name


    def generate(self,system_prompt,conversation_history):
        raise NotImplementedError("this is not implemented yet")