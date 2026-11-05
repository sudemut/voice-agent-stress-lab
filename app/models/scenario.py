class TestScenario:
    def __init__(self,scenario_id,name,goal,customer_info,expected_outcome,max_turns):
        self.scenario_id=scenario_id
        self.name=name
        self.goal=goal
        self.customer_info=customer_info
        self.expected_outcome=expected_outcome
        if max_turns<=0:
            raise ValueError("max_turns must be greater than zero")          
        self.max_turns=max_turns

    def get_scenario_id(self):
        return self.scenario_id
    def set_scenario_id(self,scenario_id):
        self.scenario_id=scenario_id
    def get_name(self):
        return self.name
    def set_name(self,name):
        self.name=name
    def get_goal(self):
        return self.goal
    def set_goal(self,goal):
        self.goal=goal
    def get_customer_info(self):
        return self.customer_info
    def set_customer_info(self, customer_info: dict):
        self.customer_info = customer_info
    def get_expected_outcome(self):
        return self.expected_outcome
    def get_max_turns(self):
        return self.max_turns
    def set_max_turns(self,amount):
        if amount<=0:
            raise ValueError("max_turns must be greater than zero")
        else:
            self.max_turns=amount

    def get_summary(self):
        return (f"Scenario: {self.get_name()} \nGoal is: {self.get_goal()}\nMax turns: {self.get_max_turns()}")
