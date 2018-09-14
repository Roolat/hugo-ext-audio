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

from hugo.ext.audio.entry import Entry
from hugo.ext.audio.exceptions import (
    AudioExtensionError,
    UnsupportedURLError,
    EmptyStreamError,
)
from hugo.ext.audio.state import State


class Join(Middleware):
    """Middleware for joining to the user's voice channel."""

    async def run(self, *_, ctx: Context, next: Callable, **kw):  # noqa: D102
        message = ctx.kwargs["message"]
        author = message.author

        if not isinstance(author, discord.Member):
            await message.channel.send("You're not a member of this guild.")
            return
        if not author.voice:
            await message.channel.send("You're not in a voice channel.")
            return
        #
        voice_channel = author.voice.channel
        voice_client = message.guild.voice_client

        if voice_client is None:
            try:
                voice_client = await voice_channel.connect()
            except asyncio.TimeoutError:
                await message.channel.send(
                    "Unfortunately, something wrong happened and I hasn't "
                    "joined your channel in a time."
                )
                return
        else:
            if voice_client.channel == voice_channel:
                await message.channel.send("I'm already in your voice channel.")
                return
            await voice_client.move_to(voice_channel)
        #
        await message.channel.send("Connected.")


class Leave(Middleware):
    """Middleware for leaving currently connected voice channel."""

    async def run(self, *_, ctx: Context, next: Callable, **kw):  # noqa: D102
        message = ctx.kwargs["message"]
        voice_client = message.guild.voice_client

        if voice_client is None:
            await message.channel.send("I'm not connected to voice channel.")
            return
        #
        await voice_client.disconnect(force=True)
        await message.channel.send("Disconnected.")


class Play(Middleware):
    """Middleware for playing provided audio's url in a user's voice channel."""

    async def run(
        self, *_, ctx: Context, next: Callable, url: Optional[str] = None, **kw
    ):  # noqa: D102
        state: State = MiddlewareState.get_state(ctx, State)
        message = ctx.kwargs["message"]
        guild = message.guild

        if url is None and state.guild_states.get(guild.id) is None:
            await message.channel.send("Provide URL to play.")
            return
        elif url:
            try:
                entry = await state.extractors["streamlink"].extract(
                    url, ctx.client.loop
                )
                state.guild_states[guild.id] = entry
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
        voice_client = message.guild.voice_client

        if voice_client is None:
            await message.channel.send("I'm not connected to voice channel.")
            return
        if voice_client.is_playing():
            voice_client.stop()
        #
        audio_source = discord.FFmpegPCMAudio(
            state.guild_states[guild.id].stream_url
        )
        audio_source = discord.PCMVolumeTransformer(audio_source)

        voice_client.play(audio_source)
        await message.channel.send("Playing...")


class Pause(Middleware):
    """Middleware for pausing currently playing audio."""

    async def run(self, *_, ctx: Context, next: Callable, **kw):  # noqa: D102
        message = ctx.kwargs["message"]
        voice_client = message.guild.voice_client

        if voice_client is None:
            await message.channel.send("I'm not connected to voice channel.")
            return
        if not voice_client._player:
            await message.channel.send("I'm not playing audio.")
            return
        if voice_client.is_paused():
            await message.channel.send("Already paused.")
            return
        #
        voice_client.pause()
        await message.channel.send("Paused.")


class Resume(Middleware):
    """Middleware for resuming currently playing audio."""

    async def run(self, *_, ctx: Context, next: Callable, **kw):  # noqa: D102
        message = ctx.kwargs["message"]
        voice_client = message.guild.voice_client

        if voice_client is None:
            await message.channel.send("I'm not connected to voice channel.")
            return
        if not voice_client._player:
            await message.channel.send("I'm not playing audio.")
            return
        if not voice_client.is_paused():
            await message.channel.send("Already playing.")
            return
        #
        voice_client.resume()
        await message.channel.send("Resumed.")


class Stop(Middleware):
    """Middleware for stopping currently playing audio."""

    async def run(self, *_, ctx: Context, next: Callable, **kw):  # noqa: D102
        message = ctx.kwargs["message"]
        voice_client = message.guild.voice_client

        if voice_client is None:
            await message.channel.send("I'm not connected to voice channel.")
            return
        if not voice_client._player:
            await message.channel.send("I'm not playing audio.")
            return
        #
        voice_client.stop()
        await message.channel.send("Stopped.")
