"""Stand-ins the tool tests share for the engine's HTTP replies."""

import io

# A token SHA-256 as the native server writes it in its blocks (10-17's probe).
SHA = "6cfce86a7e1b71d88b66e40ac527671dae0d9bf02bc9db06d46d9b03cf5c7a53"


class Reply(list):
    """What urlopen hands back: the reply's lines when iterated (a stream), their bytes joined by read()."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b"".join(self)


class BytesReply(io.BytesIO):
    """What urlopen hands back for a whole reply read at once; leaving the with block does not close it."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False
