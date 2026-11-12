import json
import os
import unittest
from unittest.mock import patch

from glm53_tf import client


class SendTests(unittest.TestCase):
    """What client.send hands urlopen: the method, URL, body, headers and timeout."""

    def sent(self, body, env):
        got = []

        def urlopen(req, timeout=None):
            got.append(
                (
                    req.get_method(),
                    req.full_url,
                    req.data,
                    req.get_header("Content-type"),
                    req.get_header("Authorization"),
                    timeout,
                )
            )
            return "reply"

        with (
            patch.object(client.urllib.request, "urlopen", urlopen),
            patch.dict(os.environ, env),
        ):
            if "TENSORFOLD_API_KEY" not in env:
                os.environ.pop("TENSORFOLD_API_KEY", None)
            self.assertEqual(
                client.send("http://127.0.0.1:8095/v1/x", body, 7), "reply"
            )
        return got[0]

    def test_a_body_is_posted_as_json_without_a_key_when_none_is_set(self):
        method, url, data, kind, key, timeout = self.sent({"a": 1}, {})
        self.assertEqual(
            (method, url, json.loads(data), kind, key, timeout),
            (
                "POST",
                "http://127.0.0.1:8095/v1/x",
                {"a": 1},
                "application/json",
                None,
                7,
            ),
        )

    def test_no_body_is_a_get(self):
        method, _, data, _, _, _ = self.sent(None, {})
        self.assertEqual((method, data), ("GET", None))

    def test_a_set_key_goes_with_every_request(self):
        for body in ({"a": 1}, None):
            with self.subTest(body=body):
                self.assertEqual(
                    self.sent(body, {"TENSORFOLD_API_KEY": "k"})[4], "Bearer k"
                )


if __name__ == "__main__":
    unittest.main()
