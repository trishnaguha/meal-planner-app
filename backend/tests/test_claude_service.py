from unittest.mock import MagicMock, patch

import pytest

from app.services.claude_service import ClaudeService


@pytest.fixture
def mock_claude():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Hello from Claude")]
    mock_client.messages.create.return_value = mock_response

    service = ClaudeService(api_key="test-key", client=mock_client)
    yield service, mock_client


def test_call_returns_text(mock_claude):
    service, mock_client = mock_claude
    result = service.call("You are helpful.", "Say hello")
    assert result == "Hello from Claude"
    mock_client.messages.create.assert_called_once()


def test_call_json_parses_response(mock_claude):
    service, mock_client = mock_claude
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"dishes": ["keema paratha"]}')]
    mock_client.messages.create.return_value = mock_response

    result = service.call_json("Parse meals.", "Saturday 5 keema paratha")
    assert result == {"dishes": ["keema paratha"]}


def test_call_json_handles_markdown_fenced_json(mock_claude):
    service, mock_client = mock_claude
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='```json\n{"dishes": ["dal"]}\n```')]
    mock_client.messages.create.return_value = mock_response

    result = service.call_json("Parse meals.", "Monday dal")
    assert result == {"dishes": ["dal"]}
