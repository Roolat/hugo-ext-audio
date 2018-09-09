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

import re

import discord

from hugo.core.constants import EventType
from hugo.core.context import Context
from hugo.core.handler import channel_type, event, not_authored_by_bot, pattern
from hugo.core.middleware import (
    MiddlewareState,
    OneOfAll,
    collection_of,
    chain_of,
)


__version__ = "1.0.0"


@event(EventType.MESSAGE)
@not_authored_by_bot()
@channel_type(guild=True)
@pattern(re.compile(r"join", re.I))
async def join(*args, ctx: Context, next, **kwargs):
    """Join to the user's voice channel."""
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
        voice_client = await voice_channel.connect()
    else:
        if voice_client.channel == voice_channel:
            await message.channel.send("I'm already in your voice channel.")
            return
        await voice_client.move_to(voice_channel)
    #
    await message.channel.send("Connected!")


@event(EventType.MESSAGE)
@not_authored_by_bot()
@channel_type(guild=True)
@pattern(re.compile(r"leave", re.I))
async def leave(*args, ctx: Context, next, **kwargs):
    """Leave currently connected voice channel."""
    message = ctx.kwargs["message"]
    voice_client = message.guild.voice_client

    if voice_client is None:
        await message.channel.send("I'm not connected to any of!")
        return
    #
    await voice_client.disconnect(force=True)
    await message.channel.send("Disconnected!")


def get_root_middleware():
    """Return root middleware chain."""
    return collection_of(OneOfAll, [join, leave])
