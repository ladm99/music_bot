import discord
from discord.ext import commands
import wavelink
import re
import random

client = commands.Bot(command_prefix='!', intents=discord.Intents.all())
URL_REGEX = re.compile(
    r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)+(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))")


class CustomPlayer(wavelink.Player):

    def __init__(self):
        super().__init__()
        self.queue = wavelink.Queue()


@client.event
async def on_ready():
    client.loop.create_task(connect_nodes())  # https and websocket operations


async def connect_nodes():
    await client.wait_until_ready()
    await wavelink.NodePool.create_node(
        bot=client,
        host='127.0.0.1',
        port=8888,
        password='youshallnotpass'
    )


@client.event
async def on_wavelink_node_ready(node: wavelink.Node):
    print(f'Node:<{node.identifier}> is ready')


@client.event
async def on_wavelink_track_end(player: CustomPlayer, track: wavelink.Track, reason):
    if not player.queue.is_empty:
        next_track = player.queue.get()
        await player.play(next_track)


@client.command(aliases=['c', 'C'])
async def connect(ctx):
    vc = ctx.voice_client
    try:
        channel = ctx.author.voice.channel
    except:
        return await ctx.send('Join a voice channel to connect')

    if not vc:
        await ctx.author.voice.channel.connect(cls=CustomPlayer())
    else:
        ctx.send('The bot is already connected to a voice channel')


@client.command(aliases=['d', 'D'])
async def disconnect(ctx):
    vc = ctx.voice_client
    if vc:
        await vc.disconnect()
    else:
        await ctx.send('The bot is not connected to a voice channel')


@client.command(aliases=['p', 'P'])
async def play(ctx, *, search: str):
    vc = ctx.voice_client

    if not vc:
        custom_player = CustomPlayer()
        vc: CustomPlayer = await ctx.author.voice.channel.connect(cls=custom_player)

    if vc.is_playing():

        if URL_REGEX.match(search):
            if 'playlist' in search:
                playlist = await wavelink.YouTubePlaylist.search(search)

                for track in playlist.tracks:
                    vc.queue.put(track)

                await ctx.send(embed=discord.Embed(
                    title=playlist.name,
                    description=f'Playing {vc.source.title} in {vc.channel}'
                ))
            else:
                node = ctx.voice_client.node
                tracks = await node.get_tracks(cls=wavelink.Track, query=search)
                vc.queue.put(tracks[0])

                await ctx.send(embed=discord.Embed(
                    title=tracks[0].title,
                    url=tracks[0].uri,
                    description=f'Playing {vc.source.title} in {vc.channel}'
                ))

        else:
            tracks = await wavelink.YouTubeTrack.search(query=search)
            vc.queue.put(tracks[0])

            await ctx.send(embed=discord.Embed(
                title=tracks[0].title,
                url=tracks[0].uri,
                description=f'Queued {vc.source.title} in {vc.channel}'
            ))
    else:
        # await vc.play(search)
        # tracks = []
        if URL_REGEX.match(search):
            if 'playlist' in search:
                playlist = await wavelink.YouTubePlaylist.search(search)

                for track in playlist.tracks:
                    vc.queue.put(track)
                await vc.play(vc.queue.get())

                await ctx.send(embed=discord.Embed(
                    title=playlist.name,
                    description=f'Playing {vc.source.title} in {vc.channel}'
                ))
            else:
                node = ctx.voice_client.node
                tracks = await node.get_tracks(cls=wavelink.Track, query=search)
                await vc.play(tracks[0])

                await ctx.send(embed=discord.Embed(
                    title=tracks[0].title,
                    url=tracks[0].uri,
                    description=f'Playing {vc.source.title} in {vc.channel}'
                ))

        else:
            tracks = await wavelink.YouTubeTrack.search(query=search)
            await vc.play(tracks[0])

            await ctx.send(embed=discord.Embed(
                title=tracks[0].title,
                url=tracks[0].uri,
                description=f'Playing {vc.source.title} in {vc.channel}'
            ))


@client.command(aliases=['q'])
async def queue(ctx, *, search: str):
    await ctx.invoke(client.get_command('play'), search=search)


@client.command(aliases=['qn', 'playnext', 'playNext'])
async def queuenext(ctx, *, search: str):
    vc = ctx.voice_client
    if URL_REGEX.match(search):
        if 'playlist' in search:
            playlist = await wavelink.YouTubePlaylist.search(search)

            for track in reversed(playlist.tracks):
                vc.queue.put_at_front(track)

            await ctx.send(embed=discord.Embed(
                title=playlist.name,
                description=f'Playing {vc.source.title} in {vc.channel}'
            ))
        else:
            node = ctx.voice_client.node
            tracks = await node.get_tracks(cls=wavelink.Track, query=search)
            vc.queue.put_at_front(tracks[0])

            await ctx.send(embed=discord.Embed(
                title=tracks[0].title,
                url=tracks[0].uri,
                description=f'Playing {vc.source.title} in {vc.channel}'
            ))

    else:
        tracks = await wavelink.YouTubeTrack.search(query=search)
        vc.queue.put_at_front(tracks[0])

        await ctx.send(embed=discord.Embed(
            title=tracks[0].title,
            url=tracks[0].uri,
            description=f'Queued {vc.source.title} in {vc.channel}'
        ))


@client.command(aliases=['s', 'S'])
async def skip(ctx):
    vc = ctx.voice_client
    if vc:
        if not vc.is_playing():
            return await ctx.send('Nothing is playing')
        if vc.queue.is_empty:
            return await vc.stop()

        await vc.seek(vc.track.length * 1000)
        if vc.is_paused():
            return await vc.resume()
    else:
        await ctx.send('The bot is not connected to a voice channel')


@client.command()
async def pause(ctx):
    vc = ctx.voice_client
    if vc:
        if vc.is_playing() and not vc.is_paused():
            await vc.pause()
        else:
            await ctx.send('Nothing is playing')
    else:
        await ctx.send('The bot is not connected to a voice channel')


@client.command(aliases=['r', 'R'])
async def resume(ctx):
    vc = ctx.voice_client
    if vc:
        if vc.is_paused():
            await vc.resume()
        else:
            await ctx.send('Nothing is paused')
    else:
        await ctx.send('The bot is not connected to a voice channel')


@client.command(aliases=['sh'])
async def shuffle(ctx):
    vc = ctx.voice_client
    if vc:
        if not vc.is_playing():
            return await ctx.send('Nothing is playing')
        if vc.queue.is_empty:
            return await ctx.send('Queue is empty')
        random.shuffle(vc.queue._queue)
        await ctx.send('The queue has been shuffled')
    else:
        await ctx.send('The bot is not connected to a voice channel')


@client.command(aliases=['sq', 'showQueue'])
async def showqueue(ctx):
    vc = ctx.voice_client
    if vc:
        if vc.queue.is_empty:
            return await ctx.send('The queue is empty')

        display_q = ''
        for x in vc.queue:
            display_q += str(x) + '\n'

        await ctx.send('`' + display_q + '`')
    else:
        await ctx.send('The bot is not connected to a voice channel')


@client.command(aliases=['clr'])
async def clear(ctx):
    vc = ctx.voice_client
    if vc:
        if vc.queue.is_empty:
            return await ctx.send('The queue is empty')
        else:
            vc.queue.clear()
            return await ctx.send('The queue has been cleared')
    else:
        await ctx.send('The bot is not connected to a voice channel')


# @play.error
# async def play_error(ctx, error):
#     if isinstance(error, commands.BadArgument):
#         await ctx.send('Could not find a track')
#     else:
#         await ctx.send('Please join a voice channel')


client.run('YOUR_TOKEN')
