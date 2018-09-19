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

from collections import defaultdict
from typing import Sequence, Type

from hugo.ext.audio.extractor import (
    Extractor,
    YouTubeDLExtractor,
    StreamlinkExtractor,
)
from hugo.ext.audio.player import Player


class State:
    """State class for audio extension related information.

    Contains different extractors' instances and current guilds' players.

    Parameters
    ----------
    extractors : Sequence[Type[:class:`hugo.ext.audio.extractor.Extractor`]]
        Extractors to initialize.

    Attributes
    ----------
    players : dict
        Map guild.id -> guild player object with current playlist, custom
        options and other info, related for that guild.
    extractors : dict
        Map with possible extractors.
    """

    def __init__(
        self,
        extractors: Sequence[Type[Extractor]] = [
            YouTubeDLExtractor,
            StreamlinkExtractor,
        ],
    ):
        self.players = defaultdict(Player)
        self.extractors = {}

        for extractor in extractors:
            instance = extractor()

            for alias in extractor.ALIASES:
                self.extractors[alias] = instance
