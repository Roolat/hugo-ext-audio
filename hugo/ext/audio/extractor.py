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

import streamlink
import youtube_dl

from hugo.ext.audio.entry import Entry, Playlist
from hugo.ext.audio.exceptions import (
    AudioExtensionError,
    EmptyStreamError,
    UnsupportedURLError,
)


class Extractor(abc.ABC):
    """Abstract extractor class.

    Attributes
    ----------
    ALIASES : list
        Alias names for extractor.
    """

    ALIASES = []

    @abc.abstractmethod
    async def extract(
        self, source_url: str, loop: asyncio.AbstractEventLoop
    ) -> Playlist:
        pass  # pragma: no cover


class YouTubeDLExtractor(Extractor):
    """Youtube-DL extractor.

    Attributes
    ----------
    ALIASES : list
        Alias names for extractor.
    OPTIONS : dict
        Youtube-DL extract options.
    session : :class:`youtube_dl.YoutubeDL`
        Youtube-DL session object.
    """

    ALIASES = ["youtube-dl", "youtubedl", "ytdl", "ydl"]

    OPTIONS = {
        "format": "bestaudio/best",
        "default_search": "auto",
        "noplaylist": True,
        "quiet": True,
    }

    def __init__(self):
        self.session = youtube_dl.YoutubeDL(params=self.OPTIONS)

    async def extract(
        self, url: str, loop: asyncio.AbstractEventLoop
    ) -> Playlist:  # noqa: D102
        try:
            info = await loop.run_in_executor(
                None,
                functools.partial(
                    self.session.extract_info, url, download=False
                ),
            )
        except Exception:
            raise AudioExtensionError()
        #
        type = info.get("_type", "video")
        playlist = Playlist()

        if type == "video":
            playlist.entries.append(Entry(info["url"], source_url=url))
        elif type == "playlist":
            playlist.source_url = url
            for info_entry in info["entries"]:
                playlist.entries.append(Entry(info_entry["url"]))
        else:
            raise UnsupportedURLError()
        #
        return playlist


class StreamlinkExtractor(Extractor):
    """Streamlink extractor.

    Attributes
    ----------
    ALIASES : list
        Alias names for extractor.
    session : :class:`streamlink.Streamlink`
        Strealink session object.
    """

    ALIASES = ["streamlink", "sl", "livestreamer", "ls"]

    def __init__(self):
        self.session = streamlink.Streamlink()

    async def extract(
        self, url: str, loop: asyncio.AbstractEventLoop
    ) -> Playlist:  # noqa: D102
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
        playlist = Playlist()
        playlist.entries.append(Entry(streams["best"].url, source_url=url))
        return playlist
