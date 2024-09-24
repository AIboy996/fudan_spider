# -*- coding: utf-8 -*-

from urllib import request
from urllib import parse

quote = lambda x: parse.quote(x.encode("utf-8"))


def bark(
    title: str,
    body: str,
    group: str,
    icon: str = "",
    isArchive: bool = True,
    token="",
    baseurl="https://api.day.app",
):
    url = f"{baseurl}/{token}?title={quote(title)}&body={quote(body)}&group={quote(group)}&isArchive={int(isArchive)}&icon={icon}"
    request.urlopen(url)


if __name__ == "__main__":
    bark("test", "body", "test")
