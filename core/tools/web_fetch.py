"""Web fetch tool with SSRF protection."""
import ipaddress
from typing import Any
from urllib.parse import urlparse

import httpx

from core.tools import register_tools
from core.tools.base import Tool, RiskLevel
from core.security.url_validator import validate_url

class WebFetchTool(Tool):
    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def description(self) -> str:
        return "Fetch a URL and return its content as text. HTTPS only."

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch (HTTPS only)"},
            },
            "required": ["url"],
        }

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.MEDIUM

    async def execute(self, input_data: dict[str, Any], *, chat_id: str) -> str:
        url = input_data["url"]

        error = validate_url(url)
        if error:
            return f"Error: {error}"

        try:
            async with httpx.AsyncClient(
                follow_redirects=False,
                timeout=10.0,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            return f"HTTP error: {e.response.status_code}"
        except httpx.RequestError as e:
            return f"Request error: {e}"

        return response.text[:50_000]


register_tools("web_fetch", lambda config: WebFetchTool())
