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
from hugo.core.handler import (
    ChannelType,
    EventConstraint,
    BotConstraint,
    Pattern,
)
from hugo.core.middleware import (
    MiddlewareState,
    OneOfAll,
    collection_of,
    chain_of,
    middleware as m,
)


__version__ = "1.0.0"


@m(EventConstraint(EventType.MESSAGE))
@m(BotConstraint(authored_by_bot=False))
@m(ChannelType(guild=True))
@m(
    collection_of(
        OneOfAll,
        [
            Pattern(re.compile(r"\bjoin\b", re.I)),
            Pattern(re.compile(r"\bconnect\b", re.I)),
        ],
    )
)
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
    await message.channel.send("Connected.")


@m(EventConstraint(EventType.MESSAGE))
@m(BotConstraint(authored_by_bot=False))
@m(ChannelType(guild=True))
@m(
    collection_of(
        OneOfAll,
        [
            Pattern(re.compile(r"\bleave\b", re.I)),
            Pattern(re.compile(r"\bdisconnect\b", re.I)),
        ],
    )
)
async def leave(*args, ctx: Context, next, **kwargs):
    """Leave currently connected voice channel."""
    message = ctx.kwargs["message"]
    voice_client = message.guild.voice_client

    if voice_client is None:
        await message.channel.send("I'm not connected to voice channel.")
        return
    #
    await voice_client.disconnect(force=True)
    await message.channel.send("Disconnected.")


@m(EventConstraint(EventType.MESSAGE))
@m(BotConstraint(authored_by_bot=False))
@m(ChannelType(guild=True))
@m(Pattern(re.compile(r"\bpause\b", re.I)))
async def pause(*args, ctx: Context, next, **kwargs):
    """Pause currently playing audio."""
    message = ctx.kwargs["message"]
    voice_client = message.guild.voice_client

    if voice_client is None:
        await message.channel.send("I'm not connected to voice channel.")
        return
    if not voice_client.is_playing():
        await message.channel.send("I'm not playing audio.")
        return
    if voice_client.is_paused():
        await message.channel.send("Already paused.")
        return
    #
    await voice_client.pause()
    await message.channel.send("Paused.")


@m(EventConstraint(EventType.MESSAGE))
@m(BotConstraint(authored_by_bot=False))
@m(ChannelType(guild=True))
@m(Pattern(re.compile(r"\bresume\b", re.I)))
async def resume(*args, ctx: Context, next, **kwargs):
    """Resume currently playing audio."""
    message = ctx.kwargs["message"]
    voice_client = message.guild.voice_client

    if voice_client is None:
        await message.channel.send("I'm not connected to voice channel.")
        return
    if not voice_client.is_playing():
        await message.channel.send("I'm not playing audio.")
        return
    if not voice_client.is_paused():
        await message.channel.send("Already playing.")
        return
    #
    await voice_client.resume()
    await message.channel.send("Resumed.")


@m(EventConstraint(EventType.MESSAGE))
@m(BotConstraint(authored_by_bot=False))
@m(ChannelType(guild=True))
@m(Pattern(re.compile(r"\bstop\b", re.I)))
async def stop(*args, ctx: Context, next, **kwargs):
    """Stop currently playing audio."""
    message = ctx.kwargs["message"]
    voice_client = message.guild.voice_client

    if voice_client is None:
        await message.channel.send("I'm not connected to voice channel.")
        return
    if not voice_client.is_playing():
        await message.channel.send("I'm not playing audio.")
        return
    #
    await voice_client.stop()
    await message.channel.send("Stopped.")


def get_root_middleware():
    """Return root middleware chain."""
    return collection_of(OneOfAll, [join, leave, pause, resume, stop])
