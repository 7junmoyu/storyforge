import re

_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


def plain_text(html: str) -> str:
    text = _TAG.sub("", html or "")
    return text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")


def count_words(html: str) -> int:
    return len(_SPACE.sub("", plain_text(html)))
