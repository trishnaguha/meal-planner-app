from unittest.mock import MagicMock, patch

import pytest

from app.agents.history_analyser import history_analyser_node


@pytest.fixture
def mock_services():
    with (
        patch("app.agents.history_analyser.claude_service") as mock_claude,
        patch("app.agents.history_analyser.chroma_service") as mock_chroma,
    ):
        mock_claude.call_json.return_value = [
            {
                "day": "Saturday",
                "dishes": ["keema paratha", "cabbage"],
                "quantity": 5,
                "prep_notes": "Make cabbage",
                "tags": ["indian", "paratha", "protein", "vegetable"],
            }
        ]
        yield mock_claude, mock_chroma


def test_history_analyser_parses_text(mock_services):
    mock_claude, mock_chroma = mock_services
    state = {
        "raw_text": "Saturday 5 keema paratha. Make cabbage",
        "input_source": "paste",
        "action": "upload",
    }

    result = history_analyser_node(state)

    assert len(result["parsed_meals"]) == 1
    assert result["parsed_meals"][0]["day"] == "Saturday"
    assert "keema paratha" in result["parsed_meals"][0]["dishes"]
    assert result["embedding_status"] == "complete"


def test_history_analyser_stores_in_chromadb(mock_services):
    mock_claude, mock_chroma = mock_services
    state = {
        "raw_text": "Saturday 5 keema paratha. Make cabbage",
        "input_source": "paste",
        "action": "upload",
    }

    history_analyser_node(state)

    mock_chroma.add_meals.assert_called_once()
    call_args = mock_chroma.add_meals.call_args[0][0]
    assert len(call_args) == 2  # two dishes: keema paratha and cabbage
    assert call_args[0]["metadata"]["dish"] == "keema paratha"


def test_history_analyser_handles_file_upload(mock_services):
    mock_claude, mock_chroma = mock_services

    with patch("app.agents.history_analyser.parse_file", return_value="Saturday 5 keema paratha"):
        state = {
            "raw_text": "",
            "uploaded_file_path": "/tmp/meals.txt",
            "input_source": "file_upload",
            "file_type": "txt",
            "action": "upload",
        }

        result = history_analyser_node(state)
        assert result["embedding_status"] == "complete"
