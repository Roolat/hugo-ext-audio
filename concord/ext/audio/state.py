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

import asyncio
import audioop
import enum
import functools
import logging
from typing import Callable, Dict, Optional, Union

import discord

from concord.ext.audio.exceptions import AudioExtensionError


log = logging.getLogger(__name__)


class State:
    """Global state with guild's audio states."""

    _audio_states: Dict[int, "AudioState"]

    def __init__(self):
        self._audio_states = {}

    def get_audio_state(
        self, voice_client_source: Union[discord.Guild, discord.abc.Connectable]
    ) -> "AudioState":
        """Returns audio state for given voice client source.

        Take a note, that returned audio state may be connected to another
        channel, due to it's voice client key is equal to given channel's key.
        Check for connected channel and move to desired one, if needed.

        Audio state will be created, if isn't created yet.

        Args:
            voice_client_source: The source, by which voice client can be
                identified (where voice client is in using) and audio state can
                be found.

        Returns:
            Audio state instance.
        """
        key_id = None

        if isinstance(voice_client_source, discord.Guild):
            key_id = voice_client_source.id
        elif isinstance(voice_client_source, discord.abc.Connectable):
            key_id, _ = voice_client_source._get_voice_client_key()

        audio_state = self._audio_states.get(key_id)
        if audio_state is None:
            audio_state = self._audio_states[key_id] = AudioState(key_id)

        return audio_state


class AudioStatus(enum.Enum):
    SOURCE_ENDED = enum.auto()
    SOURCE_CLEANED = enum.auto()
    SOURCE_REMOVED = enum.auto()
    VOICE_CLIENT_DISCONNECTED = enum.auto()
    VOICE_CLIENT_REMOVED = enum.auto()


class AudioState(discord.AudioSource):
    """Audio state class.

    Contains audio sources, voice client and other connection-related
    information for each active voice connection.

    .. warning::
        Public API is not thread safe.

    Attributes:
        _key_id: The voice client key ID this state is associated to.
        _voice_client: Voice client instance.
        _voice_client_disconnect_source: The source ``disconnect`` method of
            voice client. It's needed due to it will be replaced with a
            listener while voice client is owned by audio state.
        _loop: Loop, where main tasks of audio state should happen.
        _audio_sources: List of audio sources, with finalizers, if provided.
        _master_source: Built master source.
    """

    _key_id: int

    _voice_client: Optional[discord.VoiceClient]
    _voice_client_disconnect_source: Optional[Callable]

    _loop: asyncio.AbstractEventLoop

    _audio_sources: Dict[discord.AudioSource, Callable]
    _master_source: discord.PCMVolumeTransformer

    def __init__(self, key_id):
        self._key_id = key_id

        self._voice_client = None
        self._voice_client_disconnect_source = None

        self._loop = None

        self._audio_sources = {}
        self._master_source = discord.PCMVolumeTransformer(self)

        log.info(
            f"Audio state initialized (Voice client key ID #{self._key_id})"
        )

    @property
    def voice_client(self) -> Optional[discord.VoiceClient]:
        """Voice client of the state.

        It can be ``None``, if voice client is not created yet, or it was
        removed by disconnecting.
        """
        return self._voice_client

    @property
    def channel(self) -> discord.abc.Connectable:
        """Channel currently connected to."""
        return self._voice_client.channel if self._voice_client else None

    @property
    def guild(self) -> Optional[discord.Guild]:
        """Guild currently connected to, if applicable."""
        return self._voice_client.guild if self._voice_client else None

    @property
    def master_volume(self) -> float:
        """Master volume for all audio sources.

        Each audio source can have their own volume, if needed. Master volume
        and audio sources' volume are independent.

        Value is a float and can be from 0.0 to 2.0.
        """
        return self._master_source.volume

    @master_volume.setter
    def master_volume(self, value: float):
        self._master_source.volume = float(max(min(value, 2.0), 0.0))

    def set_voice_client(self, voice_client: discord.VoiceClient):
        """Set new voice client to the state.

        If the same client is provided, does nothing.
        If other voice client is present, it will be removed and all playing
        audio sources will be immediately finished first.

        TODO: Hey, we can change voice client, that is owned by guild/channel
        with a voice client key != our voice client key. Do something!

        Args:
            voice_client: Voice client to set.

        Raises:
            ValueError: If not a :class:`discord.VoiceClient` provided, or voice
                client is not connected.
        """
        if not isinstance(voice_client, discord.VoiceClient):
            raise ValueError("Not a voice client")
        if voice_client == self._voice_client:
            return
        if not voice_client.is_connected():
            raise ValueError("Voice client is not connected")
        if self._voice_client is not None:
            self.remove_voice_client()

        self._loop = voice_client.loop
        self._voice_client = voice_client
        self._voice_client_disconnect_source = voice_client.disconnect
        voice_client.disconnect = self._on_disconnect

        log.debug(f"Voice client has set (Voice client key ID #{self._key_id})")

    def remove_voice_client(self):
        """Removes voice client from the state.

        All currently playing audio sources will be immediately finished.
        """
        if self._voice_client is None:
            return

        self._on_end(reason=AudioStatus.VOICE_CLIENT_REMOVED)

        self._voice_client.stop()
        self._voice_client.disconnect = self._voice_client_disconnect_source
        self._voice_client_disconnect_source = None
        self._voice_client = None
        self._loop = None

        log.debug(
            f"Voice client has removed (Voice client key ID #{self._key_id})"
        )

    def add_source(
        self,
        source: discord.AudioSource,
        *,
        finalizer: Optional[Callable] = None,
    ):
        """Add audio source and transmit it via voice client.

        If audio source is already present, the ``finalizer`` will be replaced.

        Args:
            source: Audio source to add.
            finalizer: The finalizer that will be called in case of source is
                removed. Possible reasons to remove is enumerated in the
                :class:`AudioStatus`.

        Raises:
            ValueError: If not a :class:`AudioSource` instance provided.
            concord.ext.audio.exceptions.AudioExtensionError: If voice client is
                not present.
        """
        if not isinstance(source, discord.AudioSource):
            raise ValueError("Not an audio source")
        if self._voice_client is None:
            raise AudioExtensionError("Voice client is not present")
        self._audio_sources[source] = finalizer

        log.debug(f"Source has added (Voice client key ID #{self._key_id})")

        # TODO: Fast adding after player stopping can clean this source as well.
        if self._voice_client._player is None:
            self._voice_client.play(self._master_source)

    def remove_source(
        self, source: discord.AudioSource, *, reason=AudioStatus.SOURCE_REMOVED
    ):
        """Remove audio source and stop transmit it via voice client.

        Args:
            source: Audio source to remove.
            reason: Reason, provided to the audio source's finalizer.

        Raises:
            KeyError: If source is not present.
        """
        finalizer = self._audio_sources.pop(source)
        finalizer(source, reason)
        log.debug(f"Source has removed (Voice client key ID #{self._key_id})")

    def _on_end(self, *, reason=AudioStatus.SOURCE_REMOVED):
        while len(self._audio_sources) > 0:
            for source in self._audio_sources:
                try:
                    self.remove_source(source, reason=reason)
                except KeyError:
                    continue

    async def _on_disconnect(self, *args, **kwargs):
        await self._voice_client_disconnect_source(*args, **kwargs)
        self._on_end(reason=AudioStatus.VOICE_CLIENT_DISCONNECTED)
        self.remove_voice_client()

    def read(self) -> bytes:
        fragments = []

        # TODO: We need to fix this somehow...
        # Copying dict each time is not a good way
        for source in self._audio_sources.copy():
            fragment = source.read()
            if len(fragment) == 0:
                self._loop.call_soon_threadsafe(
                    functools.partial(
                        self.remove_source,
                        source,
                        reason=AudioStatus.SOURCE_ENDED,
                    )
                )
                continue
            fragments.append(fragment)

        if len(fragments) == 0:
            return b""
        min_size = functools.reduce(
            lambda x, y: min(x, len(y)), fragments, len(fragments[0])
        )
        fragments = [
            fragment[0:min_size] if len(fragment) > min_size else fragment
            for fragment in fragments
        ]

        return functools.reduce(lambda x, y: audioop.add(x, y, 2), fragments)

    def cleanup(self):
        self._voice_client.stop()
        self._loop.call_soon_threadsafe(
            functools.partial(self._on_end, reason=AudioStatus.SOURCE_CLEANED)
        )
