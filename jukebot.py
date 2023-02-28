import asyncio

import pytube
from modules.get_stream import new_dl #now uses yt-dlp

import discord
from discord.ext import commands

class jukebox:
    def __init__(self, channel):
        ###class vars
        self.channel = channel
        self.voice_client = None
    
    async def connect(self):
        ###join voice channel
        self.voice_client = await self.channel.connect()
        
    async def pause_resume(self):
        ###pause if playing or resume when paused
        if self.voice_client.is_paused():
            self.voice_client.resume()
        else:
            self.voice_client.pause()
        
    async def play(self, play_url):
        ###playing stream
        self.voice_client.play(discord.FFmpegPCMAudio(executable='C:/ffmpeg/bin/ffmpeg.exe', source=play_url, before_options='-err_detect explode -re'))
        
    def is_playing(self):
        return not self.voice_client == None and self.voice_client.is_playing()

class playlist:
    def __init__(self, channel_id):
        ###data about the playlist
        self.id = channel_id
        
        ###class vars
        self.playlist = []
        self.jukebox = {"box":None,"channel":None}
        
    async def request(self, input, ctx, is_yt_url=True):
            #actually don't want ctx in here, to much connection te class 1
            
        await self.check_jukebox(ctx)
            
        ###Get youtube url
        if is_yt_url:
            yt_url = input
            yt_title = new_dl.get_audio_stream(yt_url)["title"]
        else:
                #useless at this point
            result = pytube.Search(input).results[0]
            yt_url = result.watch_url
            yt_title = result.title
            
        self.playlist += [{"yt_url":yt_url, "yt_title":yt_title}]
        
        await ctx.send(f'Added {yt_title} to playlist')
        
        ###start playing if it is not playing
        if self.jukebox["box"].voice_client == None or not self.jukebox["box"].voice_client.is_playing():
            await self.next()
        
    async def pause_resume(self):
        await self.jukebox["box"].pause_resume()
    
    async def next(self):
        ###check if jukebox already playing
        if self.jukebox["box"].voice_client.is_playing():
           self.jukebox["box"].voice_client.stop() 
    
        ###convert youtube url to stream url
        yt_url = self.playlist[0]["yt_url"]
        play_url = new_dl.get_audio_stream(yt_url)["url"]
        
        print(play_url)
        
        ###sends play_url to jukebox
        await self.jukebox["box"].play(play_url)
        self.playlist.pop(0)
        
        ###awaits next song
        await self.song_end()
        
    async def song_end(self):
        while True:
            await asyncio.sleep(1)
            if not self.jukebox["box"].voice_client.is_playing():
                if len(self.playlist) > 0:
                    await self.next()
                return

    async def check_jukebox(self, ctx):
            #complete jank idk, doesnt connect when song ended and new song
            
        ###Create jukebox and retrieve id index
        if not ctx.author.voice.channel.id == self.jukebox["channel"] or self.jukebox["box"].voice_client == None or not self.jukebox["box"].voice_client.is_connected():
            self.jukebox["box"] = jukebox(ctx.author.voice.channel)
            await self.jukebox["box"].connect()
            self.jukebox["channel"] = ctx.author.voice.channel.id
        

class client:
    def __init__(self):
        ###class vars
        self.playlists = {"lists":[],"channels":[]}
        self.pending_options = {"types":[],"channels":[],"options":[],"ctx":[],"message":[]}

        ###bot stuff
        self.token = 'MTAzODUwNzIxNDMwODEzMDg0Nw.Gq6yK2.NmGmahw4biYN9stOR8KKq1Tyl0QrI3mS359gqQ'
        self.bot = commands.Bot(command_prefix = '?', Intents=discord.Intents.all())
        
            #need to find event to register when bot is actually connected to vc
        
        @self.bot.event
        async def on_ready():
            print('Rubiris is ready!')
        
        @self.bot.event
        async def on_raw_reaction_add(payload):
            if payload.channel_id in self.pending_options["channels"] and not payload.member.id == self.bot.user.id:
                    
                ###Getting correct options
                pending_option_index = self.pending_options["channels"].index(payload.channel_id)
                    #ctx is only used for self.playlist (want to remove)
                ctx = self.pending_options["ctx"][pending_option_index]
                
                ###deleting message
                ###Works by getting the context of a pending_option in the same channel, this way it can find the message to destroy (it requires an earlier pending message in the same channel)
                if payload.emoji.name == '❌':
                    await self.pending_options["message"][pending_option_index].delete()
                
                ###options that make user able to select title
                if self.pending_options["types"][pending_option_index] == 'title':
                    ###choosing a title
                    if payload.emoji.name in ['1⃣','2⃣','3⃣','4⃣','5⃣']:
                        if payload.emoji.name == '1⃣':
                            url = self.pending_options["options"][pending_option_index][0]
                        elif payload.emoji.name == '2⃣':
                            url = self.pending_options["options"][pending_option_index][1]
                        elif payload.emoji.name == '3⃣':
                            url = self.pending_options["options"][pending_option_index][2]
                        elif payload.emoji.name == '4⃣':
                            url = self.pending_options["options"][pending_option_index][3]
                        elif payload.emoji.name == '5⃣':
                            url = self.pending_options["options"][pending_option_index][4]
                        
                        playlists_index = self.check_playlist(payload.channel_id)
                        await self.playlists["lists"][playlists_index].request(url, ctx, is_yt_url=True)  

        ###create commands
        ###test ping
        @self.bot.command(help = 'Returns message saying "pong"')
        async def ping(ctx):
            await ctx.send('pong')
            
        ###next song
        @self.bot.command(help = 'Plays next song')
        async def next(ctx):
            ###play next song
            playlists_index = self.check_playlist(ctx.channel.id)
            await self.playlists["lists"][playlists_index].next()
        
        ###Pause or resume songs
        @self.bot.command(help = 'Pauses or resumes song')
        async def pause(ctx):
            playlists_index = self.check_playlist(ctx.channel.id)
                #transfer to class 2
            if self.playlists["lists"][playlists_index].jukebox["box"].is_playing():
                await self.playlists["lists"][playlists_index].pause_resume()
            else:
                await self.playlists["lists"][playlists_index].pause_resume()   
        
        ###request a song to be played
        @self.bot.command(help = 'Request a song to play')
        async def request(ctx, *args):
            if ctx.author == self.bot.user:
                return
            
            ###check if author is connected to voice channel
            if ctx.author.voice == None:
                await ctx.send(f'You are not connected to a voice channel')
                return
            
            ###local vars
            input = " ".join(args)
            playlists_index = self.check_playlist(ctx.channel.id)
            
            ###if search is a title
            if not (len(args) == 1 and 'http' in args[0]):
                    #seems to do 2 pytube searches
            
                ###creates list of titles
                results = pytube.Search(input).results #most diffucult webscraper in the world ...
                description = ''
                n = 0
                song_urls = []
                for result in results:
                    if n >= 5:
                        break
                    
                    song_urls += [result.watch_url]
                    description += f'{str(n+1)}. {result.title}\n'
                    n+=1
                
                ###ask question with embed and emoji reactions
                embed = discord.Embed(title='Choose a title', description=description, color=0xaa8800)
                options_message = await ctx.send(embed=embed)
                await self.add_pending_options({"channel":ctx.channel.id, "type":'title', "options":song_urls, "ctx":ctx, "message":options_message}, ctx.channel.id)
                
                ###add all reaction options
                    #takes toooo long, creates bugs
                await options_message.add_reaction('1⃣')
                await options_message.add_reaction('2⃣')
                await options_message.add_reaction('3⃣')
                await options_message.add_reaction('4⃣')
                await options_message.add_reaction('5⃣')
                await options_message.add_reaction('❌')
                
                return
                
            ###send request to class 2
            await self.playlists["lists"][playlists_index].request(input, ctx, is_yt_url=True)
        
        ###get info on playlist
        @self.bot.command(help = 'Retrieves playlist data from text channel')
        async def playlist(ctx, *args):
                #currently only id, but in future also next songs and N songs
        
            playlists_index = self.check_playlist(ctx.channel.id)
            playlist = self.playlists["lists"][playlists_index]
            
            output = ''
            if ('next' in args or len(args) == 0) and len(playlist.playlist) > 0:
                output += f'next: {playlist.playlist[-1]["yt_title"]}\n'
                
            if 'length' in args or len(args) == 0:
                output += f'length: {len(playlist.playlist)}\n'
                
            if 'id' in args or len(args) == 0:
                output += f'id: {playlist.id}\n'
                
            await ctx.send(output)

    def check_playlist(self, channel_id):
        ###Create playlist and retrieve id index
        if not channel_id in self.playlists["channels"]:
            self.playlists["channels"] += [channel_id]
            self.playlists["lists"] += [playlist(channel_id)]
        
            #need to store self.playlists in json file for in-between-sesions storage
        
        return self.playlists["channels"].index(channel_id)
    
    async def add_pending_options(self, options_object, message_id):
        if not id in self.pending_options["channels"]:
            ###new options message
            self.pending_options["channels"] += [options_object["channel"]]
            self.pending_options["types"] += [options_object["type"]]
            self.pending_options["options"] += [options_object["options"]]
            self.pending_options["ctx"] += [options_object["ctx"]]
            self.pending_options["message"] += [options_object["message"]]
        else:
            option_index = self.pending_options["channels"].index(message_id)
            
            ###delete previous options message
            if not await is_message_deleted(options_object["ctx"], message_id):
                await self.pending_options["message"][option_index].delete()
            
            ###add new options message
            self.pending_options["channels"] = options_object["channel"]
            self.pending_options["types"] = options_object["type"]
            self.pending_options["options"] = options_object["options"]
            self.pending_options["ctx"] = options_object["ctx"]
            self.pending_options["message"] = options_object["message"]
            
    async def is_message_deleted(ctx, message_id):
        try:
            await ctx.fetch_message(message_id)
            return False
        except:
            return True
    
    def run(self):
        ###runs bot in discord
        self.bot.run(self.token)
        
    async def close(self):
        ###closes bot from discord
        await self.bot.logout()
            #not used at the moment

###creates and runs a client
client = client()
client.run()

"""
Playlist is connected to one text channel
Playlist can create a jukebox which plays the current song from the playlist
Records (playlists) can be stored in an extern JSON file (not yet)
Multiple jukeboxes can be connected to a voice channel
"""


"""
Known bugs:
-Can't select too fast from pending options (when bot is still reacting with stickers), results in errors, can be solved by clicken the sticker again
-tells me all thing aren't iterables, idk, breaks completely
-sometimes the options message deletes itself, has to do with incomplete code where I tried to just have 1 options message at a time
-Music stops during the song (its not because of the song_end() fuction, it just stops o its own)
"""

"""
To-be-added features:
-Shuffle
-Records

use zip / dict / enumerate
"""