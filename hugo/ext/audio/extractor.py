"""
The MIT License (MIT)

Copyright (c) 2017-2018 Nariman Safiulin

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import abc
import asyncio
import functools
from typing import Sequence

import streamlink
import youtube_dl

from hugo.ext.audio.entry import Entry
from hugo.ext.audio.exceptions import (
    AudioExtensionError,
    UnsupportedURLError,
    EmptyStreamError,
)


class Extractor(abc.ABC):
    async def extract(
        self, source_url: str, loop: asyncio.AbstractEventLoop
    ) -> Sequence[Entry]:
        pass  # pragma: no cover


class YouTubeDLExtractor(Extractor):

    OPTIONS = {
        "format": "bestaudio/best",
        "default_search": "auto",
        "noplaylist": True,
        "quiet": True,
    }

    def __init__(self):
        self.session = youtube_dl.YoutubeDL(params=self.OPTIONS)

    async def extract(self, url: str, loop: asyncio.AbstractEventLoop) -> Entry:
        try:
            info = await loop.run_in_executor(
                None,
                functools.partial(
                    self.session.extract_info, url, download=False
                ),
            )
            type = info.get("_type", "video")
        except Exception:
            raise AudioExtensionError()
        if type == "video":
            return [Entry(url, info["url"])]
        elif type == "playlist":
            return [
                Entry(url, info_entry["url"]) for info_entry in info["entries"]
            ]
        else:
            raise UnsupportedURLError()


class StreamlinkExtractor(Extractor):
    def __init__(self):
        self.session = streamlink.Streamlink()

    async def extract(self, url: str, loop: asyncio.AbstractEventLoop) -> Entry:
        try:
            streams = await loop.run_in_executor(
                None, functools.partial(self.session.streams, url)
            )
        except streamlink.NoPluginError:
            raise UnsupportedURLError()
        except streamlink.PluginError:
            raise AudioExtensionError()
        #
        if not streams:
            raise EmptyStreamError()
        if "best" not in streams:
            raise EmptyStreamError()
        #
        return [Entry(url, streams["best"].url)]
