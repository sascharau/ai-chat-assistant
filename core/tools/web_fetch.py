"""Web fetch tool with SSRF protection."""
import ipaddress
from typing import Any
from urllib.parse import urlparse

import httpx

from core.tools import register_tools
from core.tools.base import Tool, RiskLevel


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

        error = _validate_url(url)
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


def _validate_url(url_string: str) -> str | None:
    """Validate URL against SSRF. Returns error message or None if OK."""
    try:
        parsed = urlparse(url_string)
    except ValueError:
        return "Invalid URL"

    if parsed.scheme != "https":
        return "Only HTTPS URLs are allowed"

    if not parsed.hostname:
        return "No hostname in URL"

    hostname = parsed.hostname.lower()

    # Localhost
    if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "[::1]"):
        return "Localhost URLs are blocked"

    # Private IPs
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            return "Private/local IP addresses are blocked"
    except ValueError:
        pass  # Hostname, not IP -- OK

    # Cloud metadata
    if hostname in ("169.254.169.254", "metadata.google.internal"):
        return "Cloud metadata endpoints are blocked"

    # Credentials in URL
    if parsed.username or parsed.password:
        return "URLs with credentials are blocked"

    return None


register_tools("web_fetch", lambda config: WebFetchTool())
