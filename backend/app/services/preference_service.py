import json
import os

from app.config import settings


class PreferenceService:
    def __init__(self, path: str | None = None):
        self._path = path or os.path.join(
            os.path.dirname(settings.chroma_db_path), "preferences.json"
        )

    def get(self) -> dict | None:
        if not os.path.exists(self._path):
            return None
        try:
            with open(self._path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def save(self, dietary_preference: str) -> dict:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        data = {"dietary_preference": dietary_preference}
        with open(self._path, "w") as f:
            json.dump(data, f, indent=2)
        return data


preference_service = PreferenceService()
