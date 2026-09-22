import json
import os
from unittest.mock import patch

import pytest

from app.services.preference_service import PreferenceService


@pytest.fixture
def tmp_prefs_path(tmp_path):
    return str(tmp_path / "preferences.json")


@pytest.fixture
def service(tmp_prefs_path):
    return PreferenceService(path=tmp_prefs_path)


def test_get_returns_none_when_no_file(service):
    result = service.get()
    assert result is None


def test_save_creates_file_and_returns_preference(service, tmp_prefs_path):
    result = service.save("protein and vegetables with carbohydrate")
    assert result == {"dietary_preference": "protein and vegetables with carbohydrate"}
    assert os.path.exists(tmp_prefs_path)


def test_get_returns_saved_preference(service):
    service.save("high protein meals")
    result = service.get()
    assert result == {"dietary_preference": "high protein meals"}


def test_save_overwrites_existing(service):
    service.save("old preference")
    service.save("new preference")
    result = service.get()
    assert result == {"dietary_preference": "new preference"}


def test_get_returns_none_for_corrupt_file(service, tmp_prefs_path):
    os.makedirs(os.path.dirname(tmp_prefs_path), exist_ok=True)
    with open(tmp_prefs_path, "w") as f:
        f.write("not valid json")
    result = service.get()
    assert result is None
