import asyncio
import json
import random

token = json.load(open('key.json'))["key"]

from modules.radio_soup import radio_soup

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

class mediator:
    def __init__(self, channel_id):
        ###data about the playlist
        self.id = channel_id
        
        ###class vars
        self.jukebox = {"box":None,"channel":None}
        
    async def request(self, play_url, radio_name, ctx):
            #actually don't want ctx in here, to much connection te class 1
        await self.check_jukebox(ctx)
        
            #Needs to go to class 1
        await ctx.send(f'Now playing {radio_name}')
            
        ###check if jukebox already playing
        if self.jukebox["box"].voice_client.is_playing():
           self.jukebox["box"].voice_client.stop() 
        
        ###sends play_url to jukebox
        await self.jukebox["box"].play(play_url)
        
        ###awaits song end
        await self.song_end()
        
    async def pause_resume(self):
        await self.jukebox["box"].pause_resume()
        
    async def song_end(self):
            #Useless at this point
        while True:
            await asyncio.sleep(1)
            if not self.jukebox["box"].voice_client.is_playing():
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
        self.mediators = {"mediators":[],"channels":[]}
        self.pending_options = {"type":[],"channel":[],"options":[],"ctx":[],"message":[]}
        self.reactions = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣']

        ###bot stuff
        self.bot = commands.Bot(command_prefix = '?', Intents=discord.Intents.all())
        
            #need to find event to register when bot is actually connected to vc
        
        @self.bot.event
        async def on_ready():
            print('Rubiris is ready!')
        
        @self.bot.event
        async def on_raw_reaction_add(payload):
            if payload.channel_id == self.pending_options["channel"] and not payload.member.id == self.bot.user.id:
                    
                ###Getting correct options
                    #ctx is only used for self.playlist (want to remove)
                ctx = self.pending_options["ctx"]
                
                ###deleting message
                ###Works by getting the context of a pending_option in the same channel
                    #earlier pending_options are to be destroyed when check_playlist
                if payload.emoji.name == '❌':
                    await self.pending_options["message"].delete()
                    return
                
                ###options that make user able to select title
                if self.pending_options["type"] == 'radio':
                    ###choosing a title
                    reaction = payload.emoji.name
                    
                    option_index = self.reactions.index(reaction)
                    input = self.pending_options["options"][option_index]
                    
                    ###requesting the radio
                    mediator_index = self.check_playlist(payload.channel_id)
                    await self.mediators["mediators"][mediator_index].request(input["url"], input["radio_name"], ctx) 
                    return

        ###create commands
        ###test ping
        @self.bot.command(help = 'Returns message saying "pong"')
        async def ping(ctx):
            await ctx.send('pong')
        
        ###Pause or resume songs
        @self.bot.command(help = 'Pauses or resumes song')
        async def pause(ctx):
            mediator_index = self.check_playlist(ctx.channel.id)
                #transfer to class 2
            if self.mediators["mediators"][mediator_index].jukebox["box"].is_playing():
                await self.mediators["mediators"][mediator_index].pause_resume()
            else:
                await self.mediators["mediators"][mediator_index].pause_resume()

        @self.bot.command(help = 'Pauses or resumes song')
        async def resume(ctx):
            mediator_index = self.check_playlist(ctx.channel.id)
                #transfer to class 2
            if self.mediators["mediators"][mediator_index].jukebox["box"].is_playing():
                await self.mediators["mediators"][mediator_index].pause_resume()
            else:
                await self.mediators["mediators"][mediator_index].pause_resume()                 
        
        ###request a song to be played
        @self.bot.command(help = 'Request a radio to listen to {Radio name/genre}')
        async def search(ctx, *args):
            if ctx.author == self.bot.user:
                return
            
            ###check if author is connected to voice channel
            if ctx.author.voice == None:
                await ctx.send(f'You are not connected to a voice channel')
                return
            
            ###local vars
            input = " ".join(args)
            mediator_index = self.check_playlist(ctx.channel.id)
            
            ###if search is a title
            if not (len(args) == 1 and 'http' in args[0]):
            
                ###creates list of titles
                results = radio_soup.get_stream(args[0])
                
                description = ''
                n = 0
                urls = []
                
                for result in results:
                    if n >= 5:
                        break
                        
                    ###Get nice radio name to show
                    file_type = result.split('.')[-1]
                    radio_name = result.split('/')[-1].split('.')[-2].split('_')[0]
                    
                    urls += [{"url":result, "radio_name":radio_name}]
                    description += f'{str(n+1)}. {radio_name} - .{file_type}\n'
                    n+=1
                
                ###ask question with embed and emoji reactions
                embed = discord.Embed(title='Choose a title', description=description, color=0xaa8800)
                options_message = await ctx.send(embed=embed)
                await self.add_pending_options({"channel":ctx.channel.id, "type":'radio', "options":urls, "ctx":ctx, "message":options_message},ctx.channel.id)
                
                ###add all reaction options
                for i in range(len(urls)):
                    await options_message.add_reaction(self.reactions[i])
                    
                await options_message.add_reaction('❌')
                
                return
                
            ###send request to class 2
            await self.mediators["mediators"][mediator_index].request(input, ctx)
        
        @self.bot.command(help = 'Searches random radio')
        async def tuner(ctx, *args):
            radio_urls = radio_soup.get_stream('')
            radio_url = random.choice(radio_urls)
            
            radio_name = radio_url.split('/')[-1].split('.')[-2].split('_')[0]
            
            ###requesting the radio
            mediator_index = self.check_playlist(ctx.channel.id)
            await self.mediators["mediators"][mediator_index].request(radio_url, radio_name, ctx) 
        
        @self.bot.command(help = 'Removes earlier option messages {number of messages to check}')
        async def clean(ctx, *args):
            limit = 100
        
            if len(args) > 0 and type(args[0]) == int:
                limit = args[0]
            
            async for message in ctx.channel.history(limit=limit):
                reactions = []
                for reaction in message.reactions:
                    reactions += [reaction.emoji]
                    
                if len(reactions) > 0 and '❌' in reactions and '1⃣' in reactions:
                    await message.delete()

    def check_playlist(self, channel_id):
            #need to store self.mediators in json file for in-between-sesions storage
        ###Create playlist and retrieve id index
        if not channel_id in self.mediators["channels"]:
            self.mediators["channels"] += [channel_id]
            self.mediators["mediators"] += [mediator(channel_id)]
        
        return self.mediators["channels"].index(channel_id)
    
    async def add_pending_options(self, options_object, message_id):
        if not message_id == self.pending_options["channel"]:
            ###new options message
            self.pending_options = options_object
        else:            
            ###delete previous options message
            try:
                await self.pending_options["message"].delete()
            except:
                pass
            
            ###add new options message
            self.pending_options = options_object
    
    def run(self, token):
        ###runs bot in discord
        self.bot.run(token)
        
    async def close(self):
        ###closes bot from discord
        await self.bot.logout()
            #not used at the moment

###creates and runs a client
client = client()
client.run(token)

"""
Playlist is connected to one text channel
Playlist can create a jukebox which plays the current song from the playlist
Records (playlists) can be stored in an extern JSON file (not yet)
Multiple jukeboxes can be connected to a voice channel
"""


"""
Known bugs:
-Can't select too fast from pending options (when bot is still reacting with stickers), results in errors, can be solved by clicking the sticker again
-Every command needs to specify arguments
"""

"""
To-be-added features:
-When a radio stops, search new zender
-Using a exit sequence instead of plain ^C
-(use zip / dict / enumerate)
"""