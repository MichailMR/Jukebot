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
        self.jukebox = {"box":None, "channel":None, "radio_name":None}
        
    async def request(self, play_url, radio_name, ctx):
            #actually don't want ctx in here, to much connection te class 1
        await self.check_jukebox(ctx)
        
        self.jukebox["radio_name"] = radio_name
            
        ###check if jukebox already playing
        if self.jukebox["box"].voice_client.is_playing():
           self.jukebox["box"].voice_client.stop() 
        
        ###sends play_url to jukebox
        await self.jukebox["box"].play(play_url)
        
    async def tuner(self, ctx):
            #remove ctx pls
        ###Get all radio streams
        results = radio_soup.get_stream('')
        
        ###Select a random radio stream
        n = int(random.random()*len(results["urls"]))
        radio_url, radio_name = results["urls"][n], results["radio_names"][n]
        self.jukebox["radio_name"] = radio_name
        
        ###requesting the radio stream
        await self.request(radio_url, radio_name, ctx)
        
    async def pause_resume(self):
        await self.jukebox["box"].pause_resume()

    async def check_jukebox(self, ctx):
            #Source of the ctx problem (remove ctx)
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

        ###bot stuff
        self.bot = commands.Bot(command_prefix = '?', Intents=discord.Intents.all())
        
            #need to find event to register when bot is actually connected to vc
        
        @self.bot.event
        async def on_ready():
            print('Rubiris is ready!')
        
        @self.bot.event
        async def on_raw_reaction_add(payload):
            channel_id, member_id = payload.channel_id, payload.member.id
            if channel_id == self.pending_options["channel"] and not member_id == self.bot.user.id:
                    #Need to add that it ist possible with non options message and remove reactions.remove()
                    
                ###Getting correct options
                    #ctx is only used for self.playlist (want to remove)
                ctx = self.pending_options["ctx"]
                
                ###options that make user able to select title
                if self.pending_options["type"] == 'search':
                    ###choosing a title
                    reaction = payload.emoji.name
                    
                    reactions = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '📻']
                    
                    if reaction == '📻':
                        await ctx.invoke(self.bot.get_command('radio'))
                        return
                    
                    option_index = reactions.index(reaction)
                    input = self.pending_options["options"][option_index]
                    
                    ###requesting the radio
                    mediator = self.mediators["mediators"][self.check_mediator(channel_id)]
                    await mediator.request(input["url"], input["radio_name"], ctx) 
                    await self.sync_radio_text(channel_id)
                    return
                    
                if self.pending_options["type"] == 'radio':
                    ###choosing a title
                    reaction = payload.emoji.name
                    
                    if reaction == '👍':
                        pass
                    elif reaction == '👎':
                        pass
                    elif reaction == '📡':
                        await ctx.invoke(self.bot.get_command('tuner'))
                    elif reaction == '⏯️':
                        await ctx.invoke(self.bot.get_command('pause'))
                    elif reaction == '🔎':
                        await ctx.invoke(self.bot.get_command('search'))
                    elif reaction == '❌':
                        await self.pending_options["message"].delete()
                            #needs to be a function in each class
                        await self.mediators["mediators"][self.check_mediator(channel_id)].jukebox["box"].voice_client.disconnect()
                        
                        self.mediators["mediators"].pop(self.check_mediator(channel_id))
                        self.mediators["channels"].pop(self.check_mediator(channel_id))
                    return

        ###create commands
        ###test ping
        @self.bot.command(help = 'Returns a message saying "pong"')
        async def ping(ctx):
            await ctx.send('pong')
        
        ###Pause or resume songs
        @self.bot.command(help = 'Pauses or resumes song')
        async def pause(ctx):
            mediator_index = self.check_mediator(ctx.channel.id)
                #transfer to class 2
            if self.mediators["mediators"][mediator_index].jukebox["box"].is_playing():
                await self.mediators["mediators"][mediator_index].pause_resume()
            else:
                await self.mediators["mediators"][mediator_index].pause_resume()

        @self.bot.command(help = 'Pauses or resumes song')
        async def resume(ctx):
            mediator_index = self.check_mediator(ctx.channel.id)
                #transfer to class 2
            if self.mediators["mediators"][mediator_index].jukebox["box"].is_playing():
                await self.mediators["mediators"][mediator_index].pause_resume()
            else:
                await self.mediators["mediators"][mediator_index].pause_resume()                 
        
        ###Open radio widget (inbed with reaction options)
        @self.bot.command(help = 'Opens the radio widget (📻)')
        async def radio(ctx):
            ###Get mediator
            channel_id = ctx.channel.id
            mediator = self.mediators["mediators"][self.check_mediator(channel_id)]
            
            ###Neat description
                #Needs to be updated when a new song plays
            radio_name = mediator.jukebox["radio_name"]
            if radio_name == None:
                description = f'— Now playing nothing —'
            else:
                description = f'🎶 Now playing: {radio_name} 🎶'
            
            options_message = await ctx.send(embed=discord.Embed(description=description, color=0xaa8800))
            options = [None]*5
            
            ###add options
            await self.add_pending_options({"channel":ctx.channel.id, "type":'radio', "options":options, "ctx":ctx, "message":options_message}, ctx.channel.id)
            
            ###add all reaction options
            reactions = ['👍', '👎', '📡', '⏯️', '🔎', '❌']
            for reaction in reactions:
                await options_message.add_reaction(reaction)
            
        
        ###request a song to be played
        @self.bot.command(help = 'Request a radio to listen to (🔎) [search query]')
        async def search(ctx, *args):
            if ctx.author == self.bot.user:
                return
            
            ###check if author is connected to voice channel
            if ctx.author.voice == None:
                await ctx.send('You are not connected to a voice channel')
                return
            
            channel_id = ctx.channel.id
            mediator = self.mediators["mediators"][self.check_mediator(channel_id)]
            
                #WIP
            if not mediator.jukebox["box"] == None and mediator.jukebox["box"].is_playing() and not channel_id in self.mediators["channels"]:
                await ctx.send('Please write commands in the correct text channel')
                return
            
            #If there isn't a search query ask for it
            if len(args) == 0:
                await ctx.send('What do you want to hear?')
                
                def is_channel(m):
                    return m.channel.id == channel_id
                input = (await self.bot.wait_for("message", check=is_channel)).content
            else:
                input = ' '.join(args) 
            
            #Find radio urls using radio_soup
            results = radio_soup.get_stream(input)
            
            if len(results["urls"]) == 0:
                await ctx.send('No search results')
                return
            
            mediator_index, description, urls = self.check_mediator(ctx.channel.id), '', []
            
            ###Select five results to add to options [optimised with zip]
            for url, radio_name, i in zip(results["urls"], results["radio_names"], range(5)):
                urls += [{"url":url, "radio_name":radio_name}]
                description += f'{str(i+1)}. {radio_name}\n'
            
            ###ask question with embed and emoji reactions
            options_message = await ctx.send(embed=discord.Embed(description=description, color=0xaa8800))
            
            await self.add_pending_options({"channel":ctx.channel.id, "type":'search', "options":urls, "ctx":ctx, "message":options_message},ctx.channel.id)
            
            ###add all reaction options
            reactions = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '📻']
            
            for i in range(len(urls)):
                await options_message.add_reaction(reactions[i])
            await options_message.add_reaction(reactions[-1])
        
        @self.bot.command(help = 'Searches random radio (📡)')
        async def tuner(ctx, *args):
            channel_id = ctx.channel.id
            mediator = self.mediators["mediators"][self.check_mediator(channel_id)]
            
            await mediator.tuner(ctx)
            
            await self.sync_radio_text(channel_id)
            
        @self.bot.command(help = 'Plays audio stream from url [url]')
        async def streamurl(ctx, *args):
            if len(args) > 0:
                input = ' '.join(args)
                channel_id = ctx.channel.id
                mediator = self.mediators["mediators"][self.check_mediator(channel_id)]
                
                await mediator.request(input, 'user input', ctx)
                await self.sync_radio_text(channel_id)
        
        @self.bot.command(help = 'Removes earlier option messages [number of messages to check]')
        async def clean(ctx, *args):
            limit = 100
        
            if len(args) > 0 and type(args[0]) == int:
                limit = args[0]
            
            async for message in ctx.channel.history(limit=limit):
                reactions = []
                for reaction in message.reactions:
                    reactions += [reaction.emoji]
                    
                if len(reactions) > 0 and ('📻' in reactions or '📡' in reactions):
                    await message.delete()
        
        @self.bot.command()
        async def r(ctx):
            await ctx.invoke(self.bot.get_command('radio'))
            
        @self.bot.command()
        async def s(ctx, *args):
            await ctx.invoke(self.bot.get_command('search'), args[0])
            
        @self.bot.command()
        async def p(ctx):
            await ctx.invoke(self.bot.get_command('pause'))
            
        @self.bot.command()
        async def t(ctx):
            await ctx.invoke(self.bot.get_command('tuner'))

        @self.bot.command()
        async def c(ctx):
            await ctx.invoke(self.bot.get_command('clean'))

    def check_mediator(self, channel_id):
        ###Create playlist and retrieve id index
        if not channel_id in self.mediators["channels"]:
            self.mediators["channels"] += [channel_id]
            self.mediators["mediators"] += [mediator(channel_id)]
        
        return self.mediators["channels"].index(channel_id)
        
    async def sync_radio_text(self, channel_id):
        if not self.pending_options["type"] == 'radio':
            return
    
        mediator = self.mediators["mediators"][self.check_mediator(channel_id)]
        radio_name = mediator.jukebox["radio_name"]
        
        if radio_name == None:
            description = f'— Now playing nothing —'
        else:
            description = f'🎶 Now playing: {radio_name} 🎶'
            
        embed=discord.Embed(description=description, color=0xaa8800)
        
        await self.pending_options["message"].edit(embed=embed)
    
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
        ###logs bot out from discord
        await self.bot.close()

###creates and runs a client
client = client()
client.run(token)

"""
Known bugs:
"""

"""
To-be-added features:
-Every command needs to specify number of arguments
-Like and dislikes when tuning
-Add radio widget (to easily tune next item) (with new reaction option to open radio)
-Add disconnect
"""