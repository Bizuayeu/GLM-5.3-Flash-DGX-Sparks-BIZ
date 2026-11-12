"""One request to the engine's HTTP API as the tools here send it: the body as JSON, with the server's API key
when TENSORFOLD_API_KEY is set where the tool runs (a server started with one refuses requests without it)."""

import json
import os
import urllib.request


def headers():
    """JSON's content type, and the key's Authorization header when TENSORFOLD_API_KEY is set."""
    key = os.environ.get("TENSORFOLD_API_KEY")
    return {
        "Content-Type": "application/json",
        **({"Authorization": f"Bearer {key}"} if key else {}),
    }


def send(url, body, timeout):
    """The open response to url: body POSTed as JSON, or a GET when body is None."""
    data = None if body is None else json.dumps(body).encode()
    return urllib.request.urlopen(
        urllib.request.Request(url, data, headers()), timeout=timeout
    )
