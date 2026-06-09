"""Tiny HTTP client for the quoting backend (stdlib only).

Fusion bundles a standard CPython, so we use ``urllib`` rather than pulling in
``requests`` (installing third-party packages into Fusion's Python is fiddly).
"""

import json
import urllib.error
import urllib.request

from .. import config


def request_quote(geometry: dict, material: str, quantity: int, process: str) -> dict:
    """POST a part to the backend and return the parsed quote.

    Raises ``RuntimeError`` with a readable message on any network/HTTP failure.
    """
    url = config.API_BASE_URL.rstrip("/") + config.QUOTE_ENDPOINT
    payload = {
        "geometry": geometry,
        "material": material,
        "quantity": quantity,
        "process": process,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", "replace")
        raise RuntimeError(f"Quote service returned HTTP {err.code}.\n{body}") from err
    except urllib.error.URLError as err:
        raise RuntimeError(
            f"Could not reach the quoting service at:\n{url}\n\n"
            f"Is the backend running? ({err.reason})"
        ) from err
