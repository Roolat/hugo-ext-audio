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

import enum
import functools
from typing import Optional

import discord

from hugo.ext.audio.entry import Playlist
from hugo.ext.audio.exceptions import PlayerError


class PlayerStatus(enum.Enum):
    PLAYING = enum.auto()
    PAUSED = enum.auto()
    STOPPED = enum.auto()


class Player:
    def __init__(
        self,
        *,
        playlist: Optional[Playlist] = None,
        voice_client: Optional[discord.VoiceClient] = None,
    ):
        self.playlist = playlist or Playlist()
        self.voice_client = voice_client

        self._status = PlayerStatus.STOPPED
        self._volume = 1.0
        self._audio_source = None
        self._playlist_pos = 0

    def set_playlist(self, playlist: Playlist):
        self.playlist = playlist
        self._playlist_pos = 0

    def is_playing(self):
        return self._status == PlayerStatus.PLAYING

    def is_paused(self):
        return self._status == PlayerStatus.PAUSED

    def is_stopped(self):
        return self._status == PlayerStatus.STOPPED

    def play(self):
        if self._status == PlayerStatus.PAUSED:
            self.resume()
            return
        if self.voice_client is None:
            raise PlayerError("Voice client is not present")
        #
        self._audio_source = None

        if self._playlist_pos >= len(self.playlist.entries):
            self._playlist_pos = 0
        if self._status == PlayerStatus.PLAYING:
            self.voice_client.stop()
        #
        self._audio_source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                self.playlist.entries[self._playlist_pos].stream_url
            ),
            volume=self.volume,
        )
        self.voice_client.play(
            self._audio_source,
            after=functools.partial(
                self._on_end_playing_listener, self._audio_source
            ),
        )
        self._status = PlayerStatus.PLAYING

    def skip(self):
        if self._status == PlayerStatus.STOPPED:
            return
        self._status = PlayerStatus.PLAYING
        #
        self._playlist_pos += 1

        if self._playlist_pos >= len(self.playlist.entries):
            self.stop()
        else:
            self.play()

    def pause(self):
        if self.voice_client:
            self._status = PlayerStatus.PAUSED
            self.voice_client.pause()

    def resume(self):
        if self.voice_client:
            self._status = PlayerStatus.PLAYING
            self.voice_client.resume()

    def stop(self):
        self._status = PlayerStatus.STOPPED
        self._playlist_pos = 0
        if self.voice_client:
            self.voice_client.stop()

    # TODO: Process error
    def _on_end_playing_listener(self, audio_source, error=None):
        # If listener is called due to external change in player state, don't do
        # anyting.
        if audio_source != self._audio_source:
            return
        self.skip()

    @property
    def volume(self) -> float:
        """Volume of audio (float number from 0.0 to 2.0)."""
        return self._volume

    @volume.setter
    def volume(self, value):
        self._volume = max(min(value, 2.0), 0.0)
        if self._audio_source is not None:
            self._audio_source.volume = self._volume
