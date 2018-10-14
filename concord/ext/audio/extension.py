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

from typing import Sequence

from concord.constants import EventType
from concord.ext.base import (
    BotFilter,
    ChannelTypeFilter,
    Command,
    EventNormalization,
    EventTypeFilter,
)
from concord.extension import Extension
from concord.middleware import (
    Middleware,
    MiddlewareState,
    OneOfAll,
    chain_of,
    collection_of,
)

from concord.ext.audio.middleware import Join, Leave, Volume
from concord.ext.audio.state import State
from concord.ext.audio.version import version


class AudioExtension(Extension):
    NAME = "Audio"
    DESCRIPTION = "Audio-related functionality extension for Concord"
    VERSION = version

    def __init__(self) -> None:
        super().__init__()

        self._state = State()
        self._client_middleware = [MiddlewareState(self._state)]
        self._extension_middleware = [
            chain_of(
                [
                    Join(),
                    collection_of(
                        OneOfAll, [Command("join"), Command("connect")]
                    ),
                    ChannelTypeFilter(guild=True),
                    BotFilter(authored_by_bot=False),
                    EventTypeFilter(EventType.MESSAGE),
                    EventNormalization(),
                ]
            ),
            chain_of(
                [
                    Leave(),
                    collection_of(
                        OneOfAll, [Command("leave"), Command("disconnect")]
                    ),
                    ChannelTypeFilter(guild=True),
                    BotFilter(authored_by_bot=False),
                    EventTypeFilter(EventType.MESSAGE),
                    EventNormalization(),
                ]
            ),
            chain_of(
                [
                    Volume(),
                    Command("volume", rest_pattern="(?P<volume>.+)?"),
                    Command("master"),
                    ChannelTypeFilter(guild=True),
                    BotFilter(authored_by_bot=False),
                    EventTypeFilter(EventType.MESSAGE),
                    EventNormalization(),
                ]
            ),
        ]

    @property
    def client_middleware(self) -> Sequence[Middleware]:
        return self._client_middleware

    @property
    def extension_middleware(self) -> Sequence[Middleware]:
        return self._extension_middleware
