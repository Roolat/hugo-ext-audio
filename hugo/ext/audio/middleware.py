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
from typing import Callable, Optional

import discord

from hugo.core.context import Context
from hugo.core.middleware import Middleware, MiddlewareState

from hugo.ext.audio.exceptions import (
    AudioExtensionError,
    UnsupportedURLError,
    EmptyStreamError,
)
from hugo.ext.audio.state import State


class Join(Middleware):
    """Middleware for joining to the user's voice channel."""

    async def run(self, *_, ctx: Context, next: Callable, **kw):  # noqa: D102
        state = MiddlewareState.get_state(ctx, State)
        message = ctx.kwargs["message"]
        player = state.players[message.guild.id]
        author = message.author

        if not isinstance(author, discord.Member):
            await message.channel.send("You're not a member of this guild.")
            return
        if not author.voice:
            await message.channel.send("You're not in a voice channel.")
            return
        #
        voice_channel = author.voice.channel

        if player.voice_client is None:
            try:
                player.voice_client = await voice_channel.connect()
            except asyncio.TimeoutError:
                await message.channel.send(
                    "Unfortunately, something wrong happened and I hasn't "
                    "joined your channel in a time."
                )
                return
        else:
            if player.voice_client.channel == voice_channel:
                await message.channel.send("I'm already in your voice channel.")
                return
            await player.voice_client.move_to(voice_channel)
        #
        await message.channel.send("Connected.")


class Leave(Middleware):
    """Middleware for leaving currently connected voice channel."""

    async def run(self, *_, ctx: Context, next: Callable, **kw):  # noqa: D102
        state = MiddlewareState.get_state(ctx, State)
        message = ctx.kwargs["message"]
        player = state.players[message.guild.id]

        if player.voice_client is None:
            await message.channel.send("I'm not connected to voice channel.")
            return
        #
        player.stop()
        await player.voice_client.disconnect(force=True)
        player.voice_client = None
        await message.channel.send("Disconnected.")


class Play(Middleware):
    """Middleware for playing provided audio's url in a user's voice channel."""

    async def run(
        self,
        *_,
        ctx: Context,
        next: Callable,
        url: Optional[str] = None,
        extractor: str = "youtube-dl",
        **kw,
    ):  # noqa: D102
        state: State = MiddlewareState.get_state(ctx, State)
        message = ctx.kwargs["message"]
        player = state.players[message.guild.id]

        if url is None and len(player.playlist.entries) == 0:
            await message.channel.send("Provide URL to play.")
            return
        elif url:
            if extractor not in state.extractors:
                await message.channel.send("Extractor not found.")
                return
            #
            try:
                playlist = await state.extractors[extractor].extract(
                    url, ctx.client.loop
                )
                player.stop()
                player.set_playlist(playlist)
            except UnsupportedURLError:
                await message.channel.send("Provided URL is not supported.")
                return
            except EmptyStreamError:
                await message.channel.send(
                    "Nothing to play found by provided URL."
                )
                return
            except AudioExtensionError:
                await message.channel.send(
                    "Error during resolving provided URL."
                )
                return
        #
        if player.voice_client is None:
            await message.channel.send("I'm not connected to voice channel.")
            return
        #
        player.play()
        await message.channel.send("Playing...")


class Pause(Middleware):
    """Middleware for pausing currently playing audio."""

    async def run(self, *_, ctx: Context, next: Callable, **kw):  # noqa: D102
        state: State = MiddlewareState.get_state(ctx, State)
        message = ctx.kwargs["message"]
        player = state.players[message.guild.id]

        if player.voice_client is None:
            await message.channel.send("I'm not connected to voice channel.")
            return
        if player.is_stopped():
            await message.channel.send("I'm not playing audio.")
            return
        if player.is_paused():
            await message.channel.send("Already paused.")
            return
        #
        player.pause()
        await message.channel.send("Paused.")


class Resume(Middleware):
    """Middleware for resuming currently playing audio."""

    async def run(self, *_, ctx: Context, next: Callable, **kw):  # noqa: D102
        state: State = MiddlewareState.get_state(ctx, State)
        message = ctx.kwargs["message"]
        player = state.players[message.guild.id]

        if player.voice_client is None:
            await message.channel.send("I'm not connected to voice channel.")
            return
        if player.is_stopped():
            await message.channel.send("I'm not playing audio.")
            return
        if player.is_playing():
            await message.channel.send("Already playing.")
            return
        #
        player.resume()
        await message.channel.send("Resumed.")


class Stop(Middleware):
    """Middleware for stopping currently playing audio."""

    async def run(self, *_, ctx: Context, next: Callable, **kw):  # noqa: D102
        state: State = MiddlewareState.get_state(ctx, State)
        message = ctx.kwargs["message"]
        player = state.players[message.guild.id]

        if player.voice_client is None:
            await message.channel.send("I'm not connected to voice channel.")
            return
        if player.is_stopped():
            await message.channel.send("I'm not playing audio.")
            return
        #
        player.stop()
        await message.channel.send("Stopped.")


class Skip(Middleware):
    """Middleware for skipping currently playing audio."""

    async def run(self, *_, ctx: Context, next: Callable, **kw):  # noqa: D102
        state: State = MiddlewareState.get_state(ctx, State)
        message = ctx.kwargs["message"]
        player = state.players[message.guild.id]

        if player.voice_client is None:
            await message.channel.send("I'm not connected to voice channel.")
            return
        if player.is_stopped():
            await message.channel.send("I'm not playing audio.")
            return
        #
        player.skip()
        await message.channel.send("Skipped.")


class Volume(Middleware):
    """Middleware for change volume of audio player."""

    async def run(self, *_, ctx: Context, next: Callable, volume: Optional[str] = None, **kw):  # noqa: D102
        state: State = MiddlewareState.get_state(ctx, State)
        message = ctx.kwargs["message"]
        player = state.players[message.guild.id]

        if volume is None:
            await message.channel.send("Provide a volume value.")
            return

        try:
            volume = float(volume)
        except ValueError:
            await message.channel.send("Only float values are possible.")
            return
        #
        player.volume = volume
        await message.channel.send(f"Volume changed to {player.volume}")
