from unittest.mock import MagicMock

from app.llm import gemini_client as module
from app.llm.gemini_client import GeminiClient


def make_client(rpm, monkeypatch, clock):
    sleeps = []
    monkeypatch.setattr(module.time, "monotonic", lambda: clock[0])

    def fake_sleep(seconds):
        sleeps.append(seconds)
        clock[0] += seconds

    monkeypatch.setattr(module.time, "sleep", fake_sleep)
    client = GeminiClient("model", "fake-key", requests_per_minute=rpm)
    client.client = MagicMock()
    return client, sleeps


def test_requests_are_spaced_to_stay_under_rpm(monkeypatch):
    clock = [100.0]
    client, sleeps = make_client(12, monkeypatch, clock)

    for _ in range(3):
        client._generate_content(model="model", contents=[])

    # 12 per minute -> one request every 5 seconds.
    assert sleeps == [5.0, 5.0]
    assert client.client.models.generate_content.call_count == 3


def test_no_wait_when_enough_time_has_passed(monkeypatch):
    clock = [100.0]
    client, sleeps = make_client(12, monkeypatch, clock)

    client._generate_content(model="model", contents=[])
    clock[0] += 10
    client._generate_content(model="model", contents=[])

    assert sleeps == []


def test_no_limit_by_default(monkeypatch):
    clock = [100.0]
    client, sleeps = make_client(None, monkeypatch, clock)

    for _ in range(3):
        client._generate_content(model="model", contents=[])

    assert sleeps == []
