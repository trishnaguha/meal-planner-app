import json
import os
import tempfile

import pytest

from app.services.file_parser import parse_file, parse_text


def test_parse_text_strips_whitespace():
    result = parse_text("  Saturday 5 keema paratha  \n\n")
    assert result == "Saturday 5 keema paratha"


def test_parse_txt_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Saturday 5 keema paratha. Make cabbage\nSunday 2 dal rice")
        f.flush()
        result = parse_file(f.name, "txt")
    os.unlink(f.name)
    assert "keema paratha" in result
    assert "dal rice" in result


def test_parse_csv_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("day,dish,quantity\nSaturday,keema paratha,5\nSunday,dal rice,2\n")
        f.flush()
        result = parse_file(f.name, "csv")
    os.unlink(f.name)
    assert "Saturday" in result
    assert "keema paratha" in result


def test_parse_json_file():
    data = [
        {"day": "Saturday", "dish": "keema paratha", "quantity": 5},
        {"day": "Sunday", "dish": "dal rice", "quantity": 2},
    ]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        result = parse_file(f.name, "json")
    os.unlink(f.name)
    assert "keema paratha" in result
    assert "dal rice" in result


def test_parse_unsupported_format_raises():
    with pytest.raises(ValueError, match="Unsupported file type"):
        parse_file("/fake/path.xyz", "xyz")
