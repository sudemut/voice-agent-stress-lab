from app.models.scenario import TestScenario
from app.simulation.runner import SimulationRunner
import pytest
from app.agents.base import BaseAgent
from app.agents.customer import CustomerAgent
from app.agents.support import SupportAgent
from app.llm.client import LLMClient
from app.llm.openai_client import OpenAIClient
from unittest.mock import MagicMock


@pytest.fixture
def openai_client():
    return OpenAIClient("gpt-4o-mini","fake key")

@pytest.fixture
def client():
    return LLMClient("model namee")
def test_openai_client_initialization(openai_client):
    assert openai_client.model_name=="gpt-4o-mini"
    assert openai_client.api_key=="fake key"


def test_openai_client_inheritance(openai_client,client):
    assert isinstance(openai_client, LLMClient)

def test_openai_client_generate(openai_client):
    mock_client = MagicMock()
    mock_client.responses.create.assert_called_once_with = "Hello from mock!"
    openai_client.client=mock_client
    assert openai_client.generate("a","b")=="Hello from mock!"

def test_base_client_not_implemented(client):
    with pytest.raises(NotImplementedError):
        client.generate("a", "b")