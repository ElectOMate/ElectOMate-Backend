"""URL validity validator."""

import httpx
from urllib.parse import urlparse

def validate_url(url: str, timeout: int = 10) -> bool:
    """
    Validate URL is reachable.

    Returns True if URL is valid and reachable, False otherwise.
    """
    if not url:
        return False

    try:
        # Parse URL
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            return False

        # Check reachability with HEAD request
        response = httpx.head(url, timeout=timeout, follow_redirects=True)
        return response.status_code < 400

    except Exception as e:
        print(f"  URL validation error for {url}: {e}")
        return False
