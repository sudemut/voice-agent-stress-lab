class SimulationRunner():
    def __init__(self, scenario):
        self.scenario = scenario
        self.status = "PENDING"
        self.current_turn = 0
        self.conversation_history = []
        self.termination_reason=None
        self.tool_call_history = []

    def start_simulation(self):
        if self.status != "PENDING":
            raise ValueError("It should be in pending state")
        
        self.status="RUNNING"

    def add_message(self, role, content):
        if self.status != "RUNNING":
            raise ValueError("It should be in Running State!")
        if role not in["agent","customer"]:
            raise ValueError("Invalid role")
        if self.current_turn>=self.scenario.get_max_turns() and role=="agent":
            raise ValueError("Maximum turns reached")
        
        message= {"role": role, "content": content}
        if role=="agent":
            self.current_turn +=1
        self.conversation_history.append(message)


    def complete_simulation(self,reason="MAX_TURNS"):
        if self.status != "RUNNING":
            raise ValueError("Only a running simulation can  be completed")
        self.termination_reason = reason
        self.status= "COMPLETED"
    def fail_simulation(self):
        if self.status != "RUNNING":
            raise ValueError("Only a running simulation can  be failed")
        self.termination_reason = "ERROR"
        self.status = "FAILED"

    def add_tool_calls(self, tool_calls):
        if self.status != "RUNNING":
            raise ValueError("Simulation is not running")

        if not isinstance(tool_calls, list):
            raise ValueError("tool_calls must be a list")

        self.tool_call_history.extend(tool_calls)