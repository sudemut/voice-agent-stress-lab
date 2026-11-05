class ConversationOrchestrator:
    def __init__(self,customer_agent, support_agent,runner):
        self.customer_agent=customer_agent
        self.support_agent=support_agent
        self.runner=runner


    def prepare_history(self,perpective):
        history=self.runner.conversation_history
        perpective_conv = []
        if perpective not in ["customer", "support"]:
            raise ValueError("Invalid perspective")
        for conversation in history:
            if perpective=="support":
                if conversation['role'] == "customer":
                    perpective_conv.append({"role":"user","content": conversation['content']})

                elif conversation['role']=="agent":
                    perpective_conv.append({"role":"assistant", "content": conversation['content']})

                else:
                    raise ValueError("The role should be either agent or customer")
            elif perpective=="customer":
                if conversation['role'] == "customer":
                    perpective_conv.append({"role":"assistant","content": conversation['content']})

                elif conversation['role']=="agent":
                    perpective_conv.append({"role":"user", "content": conversation['content']})

                else:
                    raise ValueError("The role should be either agent or customer")
        return perpective_conv

    def run_turn(self):
        history_cust = self.prepare_history("customer")
        cust_resp = self.customer_agent.generate_response(history_cust)

        self.runner.add_message("customer", cust_resp.message)

        if cust_resp.end_conversation:
            return True

        history_supp = self.prepare_history("support")

        supp_resp = self.support_agent.generate_response(history_supp)

        self.runner.add_message("agent", supp_resp.message)
        if supp_resp.tool_calls:
            self.runner.add_tool_calls(supp_resp.tool_calls)

        if supp_resp.end_conversation:
            return True
        
        return False
    def run(self):
        self.runner.start_simulation()

        while self.runner.current_turn < self.runner.scenario.get_max_turns():
            try:
                if self.runner.status != "RUNNING":
                    raise ValueError("Simulation is not running")

                conversation_ended = self.run_turn()

                if conversation_ended:
                    self.runner.complete_simulation(reason="AGENT_ENDED")
                    return

            except Exception as e:
                self.runner.fail_simulation()
                print(f"Simulation failed: {e}")
                return

        self.runner.complete_simulation(reason="MAX_TURNS")