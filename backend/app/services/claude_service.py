import json
import os
import re

import anthropic

from app.config import settings


def _build_client():
    if settings.use_vertex or os.environ.get("CLAUDE_CODE_USE_VERTEX") == "1":
        from anthropic import AnthropicVertex

        project_id = settings.vertex_project_id or os.environ.get(
            "ANTHROPIC_VERTEX_PROJECT_ID", ""
        )
        region = settings.vertex_region or "us-east5"
        return AnthropicVertex(project_id=project_id, region=region)
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


class ClaudeService:
    def __init__(
        self,
        api_key: str = settings.anthropic_api_key,
        model: str = settings.claude_model,
        client=None,
    ):
        self._client = client or _build_client()
        self._model = model

    def call(self, system_prompt: str, user_message: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=8192,
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
        # Try raw parse first
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        # Find first [ or { and last ] or } to extract embedded JSON
        start_bracket = min(
            (text.find(c) for c in ("[", "{") if text.find(c) != -1), default=-1
        )
        if start_bracket == -1:
            raise json.JSONDecodeError("No JSON found in response", text, 0)
        open_char = text[start_bracket]
        close_char = "]" if open_char == "[" else "}"
        end_bracket = text.rfind(close_char)
        if end_bracket == -1:
            raise json.JSONDecodeError("No closing bracket found", text, 0)
        return json.loads(text[start_bracket : end_bracket + 1])


claude_service = ClaudeService()
