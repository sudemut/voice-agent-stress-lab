from app.models.scenario import TestScenario
from app.simulation.runner import SimulationRunner
import pytest
from app.agents.base import BaseAgent
from app.agents.customer import CustomerAgent
from app.agents.support import SupportAgent

def test_start_sim():
    scenario= TestScenario(    1, "Booking", "Book a ticket",
    {}, "success", 2)
    runner=SimulationRunner(scenario)
    runner.start_simulation()
    assert runner.status== "RUNNING"

def test_start_twice():
    scenario= TestScenario(    1, "Booking", "Book a ticket",
    {}, "success", 2)
    runner=SimulationRunner(scenario)
    runner.start_simulation()
    with pytest.raises(ValueError):
        assert runner.status == "RUNNING"
        runner.start_simulation()

def test_add_customer_message():
    scenario= TestScenario(    1, "Booking", "Book a ticket",
        {}, "success", 2)
    runner=SimulationRunner(scenario)
    runner.start_simulation()
    runner.add_message("customer","Hello")
    assert len(runner.conversation_history)==1
    assert runner.conversation_history[0]["role"] == "customer"
    assert runner.current_turn == 0

def test_add_agent_message():
    scenario= TestScenario(    1, "Booking", "Book a ticket",
        {}, "success", 2)
    runner=SimulationRunner(scenario)
    runner.start_simulation()
    runner.add_message("agent","Hello")
    assert len(runner.conversation_history)==1
    assert runner.conversation_history[0]["role"] == "agent"
    assert runner.current_turn == 1

def test_add_message_invalid_status():
    scenario= TestScenario(    1, "Booking", "Book a ticket",
        {}, "success", 2)
    runner=SimulationRunner(scenario)
    with pytest.raises(ValueError):
        runner.add_message("customer","Hi!")
    assert len(runner.conversation_history)==0

def test_add_message_invalid_role():
    scenario= TestScenario(    1, "Booking", "Book a ticket",
            {}, "success", 2)
    runner=SimulationRunner(scenario)
    runner.start_simulation()
    with pytest.raises(ValueError):
        runner.add_message("","hi")
    assert len(runner.conversation_history)==0
    assert runner.current_turn == 0

def test_add_message_max_turns():
    scenario= TestScenario(    1, "Booking", "Book a ticket",
                {}, "success", 2)
    runner=SimulationRunner(scenario)
    runner.start_simulation()
    runner.add_message("customer","hi")
    runner.add_message("agent","hi")
    runner.add_message("customer","can you help me with ..")
    runner.add_message("agent","ofc")
    assert runner.current_turn==2
    with pytest.raises(ValueError):
        runner.add_message("agent","a")

    assert len(runner.conversation_history) == 4

def test_complete_simulation_success():
    scenario= TestScenario(    1, "Booking", "Book a ticket",
                    {}, "success", 2)
    runner=SimulationRunner(scenario)
    runner.start_simulation()
    runner.complete_simulation()
    assert runner.status== "COMPLETED"
def test_complete_simulation_from_pending():
    scenario= TestScenario(    1, "Booking", "Book a ticket",
                    {}, "success", 2)
    runner=SimulationRunner(scenario)
    with pytest.raises(ValueError):
        runner.complete_simulation()

def test_complete_simulation_twice():
    scenario= TestScenario(    1, "Booking", "Book a ticket",
                    {}, "success", 2)
    runner=SimulationRunner(scenario)
    runner.start_simulation()
    runner.complete_simulation()
    with pytest.raises(ValueError):
        runner.complete_simulation()

def test_fail_simulation_success():
    scenario= TestScenario(    1, "Booking", "Book a ticket",
                    {}, "success", 2)
    runner=SimulationRunner(scenario)
    runner.start_simulation()
    runner.add_message("customer","hi")
    runner.fail_simulation()
    assert len(runner.conversation_history) ==1
    assert runner.status=="FAILED"

def test_fail_simulation_from_pending():
    scenario= TestScenario(    1, "Booking", "Book a ticket",
                    {}, "success", 2)
    runner=SimulationRunner(scenario)
    with pytest.raises(ValueError):
            runner.fail_simulation()

def test_fail_simulation_after_completed():
    scenario= TestScenario(    1, "Booking", "Book a ticket",
                    {}, "success", 2)
    runner=SimulationRunner(scenario)
    runner.start_simulation()
    runner.complete_simulation()
    with pytest.raises(ValueError):
        runner.fail_simulation()

def test_add_message_after_completed():
    scenario= TestScenario(    1, "Booking", "Book a ticket",
                    {}, "success", 3)
    runner=SimulationRunner(scenario)
    runner.start_simulation()
    runner.add_message("customer","hi")
    runner.complete_simulation()
    with pytest.raises(ValueError):
        runner.add_message("agent","hi")
    assert runner.current_turn==0
    assert len(runner.conversation_history)==1

def test_add_message_after_failed():
    scenario= TestScenario(    1, "Booking", "Book a ticket",
                    {}, "success", 3)
    runner=SimulationRunner(scenario)
    runner.start_simulation()
    runner.add_message("customer","hi")
    runner.fail_simulation()
    with pytest.raises(ValueError):
        runner.add_message("agent","hi")
    assert runner.current_turn==0
    assert len(runner.conversation_history)==1

def test_isCustomerAgentreach():
    scenario= TestScenario(    1, "Booking", "Book a ticket",
                    {}, "success", 3)
    ourca=CustomerAgent("our customer agent's name","our customer agent's system prompt","our llm client url", scenario)
    oursa=SupportAgent("our Support agent's name","our Support agent's system prompt","our llm client url")
    assert ourca.name=="our customer agent's name"
    assert ourca.system_prompt=="our customer agent's system prompt"
    assert oursa.name=="our Support agent's name"
    assert oursa.system_prompt=="our Support agent's system prompt"
    assert ourca.scenario is scenario