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

from concord.context import Context
from concord.middleware import Middleware, MiddlewareState

from concord.ext.audio.state import State


class Join(Middleware):
    """Middleware for joining to the user's voice channel."""

    async def run(self, *_, ctx: Context, next: Callable, **kw):  # noqa: D102
        state = MiddlewareState.get_state(ctx, State)
        if state is None:
            return

        message = ctx.kwargs["message"]
        author = message.author
        channel = message.channel

        if not isinstance(author, discord.Member):
            await channel.send("You're not a member of this guild.")
            return
        if not author.voice:
            await channel.send("You're not in a voice channel.")
            return
        #
        # Only guilds are allowed.
        voice_client = channel.guild.voice_client
        audio_state = state.get_audio_state(channel.guild)
        voice_channel = author.voice.channel

        if voice_client is None:
            try:
                voice_client = await voice_channel.connect()
            except asyncio.TimeoutError:
                await channel.send(
                    "Unfortunately, something wrong happened and I hasn't "
                    "joined your channel in a time."
                )
                return
            await channel.send("Connected.")
        elif voice_client.channel != voice_channel:
            await voice_client.move_to(voice_channel)
            await channel.send("Moved.")
        else:
            await channel.send("I'm already in your voice channel.")
        #
        audio_state.set_voice_client(voice_client)


class Leave(Middleware):
    """Middleware for leaving currently connected voice channel."""

    async def run(self, *_, ctx: Context, next: Callable, **kw):  # noqa: D102
        message = ctx.kwargs["message"]
        author = message.author
        channel = message.channel

        if not isinstance(author, discord.Member):
            await channel.send("You're not a member of this guild.")
            return
        #
        # Only guilds are allowed.
        voice_client = channel.guild.voice_client

        if voice_client is None:
            await message.channel.send("I'm not connected to voice channel.")
            return
        #
        # Voice client will be removed from audio state as well.
        await voice_client.disconnect(force=True)
        await message.channel.send("Disconnected.")


class Volume(Middleware):
    """Middleware for changing the master volume."""

    async def run(
        self,
        *_,
        ctx: Context,
        next: Callable,
        volume: Optional[str] = None,
        **kw,
    ):  # noqa: D102
        state = MiddlewareState.get_state(ctx, State)
        if state is None:
            return

        message = ctx.kwargs["message"]
        channel = message.channel
        # Only guilds are allowed.
        audio_state = state.get_audio_state(channel.guild)

        if volume is not None:
            try:
                audio_state.master_volume = float(volume)
            except ValueError:
                await channel.send("Only float values are possible.")
                return
        #
        await channel.send(
            f"Master volume is set to {audio_state.master_volume}"
        )
