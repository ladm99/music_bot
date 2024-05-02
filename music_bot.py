import discord
from discord.ext import commands
import wavelink
import re

# from wavelink.ext import spotify

client = commands.Bot(command_prefix='!', intents=discord.Intents.all())
URL_REGEX = re.compile(
    r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)+(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))")


class CustomPlayer(wavelink.Player):

    def __init__(self):
        super().__init__()
        self.queue = wavelink.Queue()


@client.event
async def on_ready():
    client.loop.create_task(connect_nodes(client))  # https and websocket operations


async def connect_nodes(self):
    #     await client.wait_until_ready()
    #     # await wavelink.Pool.create_node(
    #     #     bot=client,
    #     #     host='127.0.0.1',
    #     #     port=8888,
    #     #     password='youshallnotpass'
    #     # )
    nodes = [wavelink.Node(uri='http://localhost:7000', password='youshallnotpass')]
    await wavelink.Pool.connect(nodes=nodes, client=self, cache_capacity=100)


@client.event
async def on_wavelink_node_ready(node: wavelink.Node):
    print(f'Node:<{node.session_id}> is ready')


# async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload) -> None:
#     player: wavelink.Player | None = payload.player
#     if not player:
#         return
#
#     original: wavelink.Playable | None = payload.original
#     track: wavelink.Playable = payload.track
#
#     embed: discord.Embed = discord.Embed(title="Now Playing")
#     embed.description = f"**{track.title}** by `{track.author}`"
#
#     if track.artwork:
#         embed.set_image(url=track.artwork)
#
#     if original and original.recommended:
#         embed.description += f"\n\n`This track was recommended via {track.source}`"
#
#     if track.album.name:
#         embed.add_field(name="Album", value=track.album.name)


# @client.event
# async def on_wavelink_track_end(player: CustomPlayer, track: wavelink.tracks, reason):
#     if not player.queue.is_empty:
#         next_track = player.queue.get()
#         await player.play(next_track)


@client.command(description='Connects the bot to the same channel as you', aliases=['c', 'C'])
async def connect(ctx):
    """Connects the bot to the same channel as you"""
    vc = ctx.voice_client
    try:
        channel = ctx.author.voice.channel
    except:
        return await ctx.send('Join a voice channel to connect')

    if not vc:
        await ctx.author.voice.channel.connect(cls=CustomPlayer())
    else:
        ctx.send('The bot is already connected to a voice channel')


@client.command(description='Disconnects the bot from the voice channel', aliases=['d', 'D'])
async def disconnect(ctx):
    """Disconnects the bot from the voice channel"""
    vc = ctx.voice_client
    if vc:
        await vc.disconnect()
    else:
        await ctx.send('The bot is not connected to a voice channel')


@client.command(description='Plays song if the queue is empty, adds song to queue if it is not', aliases=['p', 'P'])
async def play(ctx, *, search: str):
    """Plays song if the queue is empty, adds song to queue if it is not"""
    vc = ctx.voice_client
    if not vc:
        custom_player = CustomPlayer()
        vc: CustomPlayer = await ctx.author.voice.channel.connect(cls=custom_player)
        if not vc.playing:
            if vc.autoplay == wavelink.AutoPlayMode.disabled:
                vc.autoplay = wavelink.AutoPlayMode.enabled

            tracks: wavelink.Search = await wavelink.Playable.search(search)
            if isinstance(tracks, wavelink.Playlist):
                await ctx.send(embed=discord.Embed(
                    title=tracks.name,
                    description=f' {tracks[0].playlist.name} in {vc.channel} added to queue'
                ))
                vc.queue.put(tracks)
            else:
                track: wavelink.Playable = tracks[0]
                await vc.play(track)
                await ctx.send(embed=discord.Embed(
                    title=track.title,
                    url=track.uri,
                    description=f'Playing {track.title} in {vc.channel} '
                ))
            if not vc.playing:
                await vc.play(vc.queue.get())
    else:
        if vc.autoplay == wavelink.AutoPlayMode.disabled:
            vc.autoplay = wavelink.AutoPlayMode.enabled

        tracks: wavelink.Search = await wavelink.Playable.search(search)
        if isinstance(tracks, wavelink.Playlist):
            await ctx.send(embed=discord.Embed(
                title=tracks.name,
                description=f' {tracks[0].playlist.name} in {vc.channel} added to queue'
            ))
            vc.queue.put(tracks)
        else:
            track: wavelink.Playable = tracks[0]
            vc.queue.put(track)
            await ctx.send(embed=discord.Embed(
                title=track.title,
                url=track.uri,
                description=f'{track.title} in {vc.channel} added to queue'
            ))
        if not vc.playing:
            await vc.play(vc.queue.get())


@client.command(description='Adds song to queue, basically the same as play', aliases=['q'])
async def queue(ctx, *, search: str):
    """Adds song to queue, basically the same as play"""
    await ctx.invoke(client.get_command('play'), search=search)


@client.command(description='Adds song to the top of the queue', aliases=['qn', 'playnext', 'playNext'])
async def queuenext(ctx, *, search: str):
    """Adds song to the top of the queue"""
    vc = ctx.voice_client
    tracks: wavelink.Search = await wavelink.Playable.search(search)
    if isinstance(tracks, wavelink.Playlist):
        await ctx.send(embed=discord.Embed(
            title=tracks.name,
            description=f' {tracks[0].playlist.name} in {vc.channel} added to queue'
        ))
        vc.queue.put(tracks)
    else:
        track: wavelink.Playable = tracks[0]
        vc.queue.put_at(0, track)
        await ctx.send(embed=discord.Embed(
            title=track.title,
            url=track.uri,
            description=f'{track.title} in {vc.channel} added to queue'
        ))


@client.command(description='Skips the current song', aliases=['s', 'S'])
async def skip(ctx):
    """Skips the current song"""
    vc = ctx.voice_client
    if vc:
        if not vc.playing:
            return await ctx.send('Nothing is playing')
        if vc.queue.is_empty:
            return await vc.stop()
        else:
            await vc.play(vc.queue.get())
        # await vc.skip()
        if vc.paused:
            return await vc.pause(False)
    else:
        await ctx.send('The bot is not connected to a voice channel')


@client.command(description='Pauses playback')
async def pause(ctx):
    """Pauses playback"""
    vc = ctx.voice_client
    if vc:
        if vc.playing and not vc.paused:
            await vc.pause(True)
        elif vc.playing and vc.pause:
            await vc.pause(False)
        else:
            await ctx.send('Nothing is playing')
    else:
        await ctx.send('The bot is not connected to a voice channel')


@client.command(description='Resumes playback', aliases=['r', 'R'])
async def resume(ctx):
    """Resumes playback"""
    vc = ctx.voice_client
    if vc:
        if vc.paused:
            await vc.pause(False)
        else:
            await ctx.send('Nothing is paused')
    else:
        await ctx.send('The bot is not connected to a voice channel')


@client.command(description='Shuffles the queue', aliases=['sh'])
async def shuffle(ctx):
    """Shuffles the queue"""
    vc = ctx.voice_client
    if vc:
        if not vc.playing:
            return await ctx.send('Nothing is playing')
        if vc.queue.is_empty:
            return await ctx.send('Queue is empty')
        vc.queue.shuffle()
        await ctx.send('The queue has been shuffled')
    else:
        await ctx.send('The bot is not connected to a voice channel')


@client.command(description='Prints out the current queue', aliases=['sq', 'showQueue'])
async def showqueue(ctx):
    """Prints out the current queue"""
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


@client.command(description='Clears the queue', aliases=['clr'])
async def clear(ctx):
    """Clears the queue"""
    vc = ctx.voice_client
    if vc:
        if vc.queue.is_empty:
            return await ctx.send('The queue is empty')
        else:
            vc.queue.clear()
            return await ctx.send('The queue has been cleared')
    else:
        await ctx.send('The bot is not connected to a voice channel')


@play.error
async def play_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send('Could not find a track')
    else:
        await ctx.send('Please join a voice channel')


client.run('YOUR_TOKEN')
