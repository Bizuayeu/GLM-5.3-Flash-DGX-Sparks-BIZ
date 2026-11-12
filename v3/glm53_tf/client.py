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


def chunks(response):
    """The JSON chunks of a streamed reply, its other lines and `data: [DONE]` left out."""
    for raw in response:
        line = raw.decode().strip()
        if line.startswith("data: ") and line != "data: [DONE]":
            yield json.loads(line[6:])


def cached(usage):
    """The prompt tokens a reply's usage says the prompt cache gave, 0 when it names none."""
    return (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
