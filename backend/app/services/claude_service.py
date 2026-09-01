import json
import re

import anthropic

from app.config import settings


class ClaudeService:
    def __init__(
        self,
        api_key: str = settings.anthropic_api_key,
        model: str = settings.claude_model,
    ):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def call(self, system_prompt: str, user_message: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    def call_json(self, system_prompt: str, user_message: str) -> dict | list:
        text = self.call(system_prompt, user_message)
        return self._extract_json(text)

    def _extract_json(self, text: str) -> dict | list:
        fenced = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
        if fenced:
            return json.loads(fenced.group(1).strip())
        return json.loads(text.strip())


claude_service = ClaudeService()
