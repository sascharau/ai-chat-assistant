"""URL validation against SSRF attacks.

- HTTPS only
- No localhost/private IPs
- No cloud metadata endpoints
- No credentials in URL
"""
import ipaddress
from urllib.parse import urlparse


def validate_url(url_string: str) -> str | None:
    """Validate a URL. Returns an error message or None if OK."""
    try:
        parsed = urlparse(url_string)
    except ValueError:
        return "Invalid URL"

    # 1. HTTPS only
    if parsed.scheme != "https":
        return "Only HTTPS URLs are allowed"

    # 2. Hostname must be present
    if not parsed.hostname:
        return "No hostname in URL"

    # 3. Block localhost
    hostname = parsed.hostname.lower()
    if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "[::1]"):
        return "Localhost URLs are blocked"

    # 4. Block private IPs
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast:
            return "Private/local IP addresses are blocked"
    except ValueError:
        pass  # Hostname, not an IP -- OK

    # 5. Block cloud metadata endpoints (AWS, GCP, Azure)
    if hostname in ("169.254.169.254", "metadata.google.internal"):
        return "Cloud metadata endpoints are blocked"

    # 6. Block credentials in URL
    if parsed.username or parsed.password:
        return "URLs with credentials are blocked"

    return None  # All OK