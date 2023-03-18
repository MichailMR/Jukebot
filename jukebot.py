import asyncio
import json
import random

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
        self.jukebox = {"box":None, "channel":None, "radio_name":None, "play_url":None}
        
    async def request(self, play_url, radio_name, ctx):
            #actually don't want ctx in here, to much connection te class 1
        await self.check_jukebox(ctx)
        
        self.jukebox["radio_name"], self.jukebox["play_url"] = radio_name, play_url
            
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
        
        self.connected = False

        ###bot stuff
        help_command = commands.DefaultHelpCommand(no_category = 'Commands')
        
        self.bot = commands.Bot(command_prefix = '?', Intents=discord.Intents.all(), help_command=help_command)
        
        @self.bot.event
        async def on_ready():
            print('Rubiris is ready!')
            
        @self.bot.event
        async def on_voice_state_update(member, before, after):
            if member.id == self.bot.user.id and (before.channel == None or after.channel == None):
                self.connected = not self.connected
        
        @self.bot.event
        async def on_raw_reaction_add(payload):
            channel_id, member_id = payload.channel_id, payload.member.id
            if channel_id == self.pending_options["channel"] and not member_id == self.bot.user.id:
                reaction = payload.emoji.name
                
                ###Remove reaction such that user can click again
                await self.pending_options["message"].remove_reaction(reaction, payload.member)
                    
                ###Getting correct options
                    #ctx is only used for self.playlist (want to remove)
                ctx = self.pending_options["ctx"]
                
                ###options that make user able to select title
                if self.pending_options["type"] == 'search':
                    ###return to radio widget
                    if reaction == '📻':
                        await ctx.invoke(self.bot.get_command('radio'))
                        return
            
                    ###choosing a title
                    reactions = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣']
                    option_index = reactions.index(reaction)
                    input = self.pending_options["options"][option_index]
                    
                    ###requesting the radio
                    mediator = self.mediators["mediators"][self.check_mediator(channel_id)]
                    await mediator.request(input["play_url"], input["radio_name"], ctx) 
                    await ctx.invoke(self.bot.get_command('radio'))
                    
                if self.pending_options["type"] == 'radio':      
                    if reaction == '🔎':
                        await ctx.invoke(self.bot.get_command('search'))                
                    elif reaction == '⏯️':
                        await ctx.invoke(self.bot.get_command('pause'))
                    elif reaction == '📡':
                        await ctx.invoke(self.bot.get_command('tuner'))
                    elif reaction == '📒':
                        await ctx.invoke(self.bot.get_command('likes'))
                    elif reaction == '👍':
                        await ctx.invoke(self.bot.get_command('like'))
                    elif reaction == '👎':
                        await ctx.invoke(self.bot.get_command('dislike'))
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
        @self.bot.command(help = '(⏯️ / pa / resume) Pauses or resumes song', aliases=['resume', 'pa'])
        async def pause(ctx):
            #Get mediator and invoke pause
            channel_id = ctx.channel.id
            mediator = self.mediators["mediators"][self.check_mediator(channel_id)]
            mediator.pause()
        
        ###Open radio widget (inbed with reaction options)
        @self.bot.command(help = '(📻 / ra / reload) Opens the radio widget', aliases=['ra', 'reload'])
        async def radio(ctx):
            ###Check if author is in voice channel to gain control
            if ctx.author.voice == None:
                    await ctx.send('You are not connected to a voice channel')
                    return
        
            ###clean earlier embedded messages
            await ctx.invoke(self.bot.get_command('clean'))
            
            ###Get mediator
            channel_id = ctx.channel.id
            mediator = self.mediators["mediators"][self.check_mediator(channel_id)]
            
            ###Open data json data base file as a dictionary 
            with open('../dict.json', 'r', encoding = 'utf8') as dict_file:
                ###retrieve data
                dict = json.loads(dict_file.read())
                author_id_str = str(ctx.author.id)
                
                if not author_id_str in list(dict["likes"]):
                    dict["likes"][author_id_str] = []
                
                likes = dict["likes"][author_id_str]
                
                ###Close file
                dict_file.close()
            
            ###Directly begin playing a liked radio when silent
            if len(likes) > 0 and (True if mediator.jukebox["box"] == None else not mediator.jukebox["box"].is_playing()):
                liked_radio = random.choice(likes)
                await mediator.request(liked_radio["play_url"], liked_radio["radio_name"], ctx) 
            
            ###Neat description to show to the user
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
            reactions = ['🔎', '⏯️', '📡', '📒', '👍', '👎', '❌']
            for reaction in reactions:
                await options_message.add_reaction(reaction)
            
        
        ###request a song to be played
        @self.bot.command(help = '(🔎 / sr) Request a radio to listen to [search query]', aliases=['sr'])
        async def search(ctx, *args):
            if ctx.author == self.bot.user:
                return
            
            ###check if author is connected to voice channel
            if ctx.author.voice == None:
                await ctx.send('You are not connected to a voice channel')
                return
            
            channel_id = ctx.channel.id
            mediator = self.mediators["mediators"][self.check_mediator(channel_id)]

            ###If there isn't a search query ask for it
            if len(args) == 0:
                await ctx.send('search a radio 🔎')
                
                def is_channel(m):
                    return m.channel.id == channel_id
                input = (await self.bot.wait_for("message", check=is_channel)).content
            else:
                input = ' '.join(args)
                
            if input[0] == '?':
                ctx.send('Please do not use commands as a search query')
                return
            
            #Find radio urls using radio_soup
            results = radio_soup.get_stream(input)
            
            if len(results["urls"]) == 0:
                await ctx.send('No search results')
                return
            
            mediator_index, description, urls = self.check_mediator(ctx.channel.id), '', []
            
            ###Select five results to add to options [optimised with zip]
            for url, radio_name, i in zip(results["urls"], results["radio_names"], range(5)):
                urls += [{"play_url":url, "radio_name":radio_name}]
                description += f'{str(i+1)}. {radio_name}\n'
            
            ###ask question with embed and emoji reactions
            options_message = await ctx.send(embed=discord.Embed(description=description, color=0xaa8800))
            
            await self.add_pending_options({"channel":ctx.channel.id, "type":'search', "options":urls, "ctx":ctx, "message":options_message},ctx.channel.id)
            
            ###add all reaction options
            reactions = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣']
            
            for i in range(len(urls)):
                await options_message.add_reaction(reactions[i])
            await options_message.add_reaction('📻')
        
        @self.bot.command(help = '(📡 / tu) Searches random radio', aliases=['tu'])
        async def tuner(ctx, *args):
            ###Check if author is in voice channel to gain control
            if ctx.author.voice == None:
                    await ctx.send('You are not connected to a voice channel')
                    return
        
            ###Get mediator
            channel_id = ctx.channel.id
            mediator = self.mediators["mediators"][self.check_mediator(channel_id)]
            
            ###Get random radio
            await mediator.tuner(ctx)
            
            ###Open / update radio widget
            await ctx.invoke(self.bot.get_command('radio'))
            
        @self.bot.command(help = 'Plays audio stream from url [url]')
        async def streamurl(ctx, *args):
            ###Allow users to play stream urls of their own finding
            if len(args) > 0:
                input = ' '.join(args)
                channel_id = ctx.channel.id
                mediator = self.mediators["mediators"][self.check_mediator(channel_id)]
                
                await mediator.request(input, 'user input', ctx)
                await self.sync_radio_text(channel_id)
        
        @self.bot.command(help = '(cl) Removes send option messages [amout of messages]', aliases=['cl'])
        async def clean(ctx, *args):
            ###maintanance command
            limit = 10
            
            ###Check for user argument
            if len(args) > 0 and type(args[0]) == int:
                limit = args[0]
            
            ###Removes all pending option messages
            async for message in ctx.channel.history(limit=limit):
                reactions = []
                for reaction in message.reactions:
                    reactions += [reaction.emoji]
                    
                if len(reactions) > 0 and ('1⃣' in reactions or '❌' in reactions):
                    await message.delete()
        
        @self.bot.command(help = '(👍 / li) Liked radio play when using the radio widget', aliases=['li'])
        async def like(ctx):
            ###Open data json data base file as a dictionary 
            with open('../dict.json', 'r+', encoding = 'utf8') as dict_file:
                ###retrieve data
                dict = json.loads(dict_file.read())
                author_id_str, channel_id = str(ctx.author.id), ctx.channel.id
                mediator = self.mediators["mediators"][self.check_mediator(channel_id)]
                
                ###Check if radio can be liked and add it to personal likes
                jukebox = mediator.jukebox
                if len(dict["likes"][author_id_str]) < 5:
                    if not jukebox["play_url"] == None and not jukebox["play_url"] in [like["play_url"] for like in dict["likes"][author_id_str]]:
                        if author_id_str in list(dict["likes"]):
                            dict["likes"][author_id_str] += [{"play_url":jukebox["play_url"], "radio_name":jukebox["radio_name"]}]
                        else:
                            dict["likes"][author_id_str] = [{"play_url":jukebox["play_url"], "radio_name":jukebox["radio_name"]}]
                    await ctx.send('liked 👍')
                else:
                    await ctx.send('max. 5 liked radio\'s')
                
                ###Overwrite the file
                dict_file.seek(0)
                dict_file.write(json.dumps(dict))    

                dict_file.truncate()
                dict_file.close()
        
        @self.bot.command(help = '(👎 / dl) Removes the radio from likes', aliases=['dl'])
        async def dislike(ctx):
            ###Open data json data base file as a dictionary 
            with open('../dict.json', 'r+', encoding = 'utf8') as dict_file:
                ###retrieve data
                dict = json.loads(dict_file.read())
                author_id_str, channel_id = str(ctx.author.id), ctx.channel.id
                mediator = self.mediators["mediators"][self.check_mediator(channel_id)]
                
                ###check if radio can be disliked and dislike
                if author_id_str in list(dict["likes"]):
                    index = [index for index, like in enumerate(dict["likes"][author_id_str]) if like["play_url"] == mediator.jukebox["play_url"]]
                    if len(index) > 0:
                        index = index[0]
                        dict["likes"][author_id_str].pop(index)
                
                ###Overwrite file
                dict_file.seek(0)
                dict_file.write(json.dumps(dict))    

                dict_file.truncate()
                dict_file.close()
                    
            await ctx.send('disliked 👎')
        
        @self.bot.command(help = '(📒 / ls) Lets you choose from your liked radio\'s', aliases=['ls'])
        async def likes(ctx):
            ###Open data json data base file as a dictionary
            with open('../dict.json', 'r', encoding = 'utf8') as dict_file:
                dict = json.loads(dict_file.read())
                author_id_str = str(ctx.author.id)
                
                if not author_id_str in dict["likes"].keys():
                    dict["likes"][author_id_str] = []
                
                likes = dict["likes"][author_id_str]
                
                    #useless
                play_urls = [like["play_url"] for like in likes]
                
                ###write a user friendly options message
                if len(likes) > 0:
                    description = ''.join([str(i+1)+'. '+like["radio_name"]+'\n' for i, like in enumerate(likes)])
                else:
                    description = 'Like a radio using the ?likes command or 👍'
                    
                options_message = await ctx.send(embed=discord.Embed(description=description, color=0xaa8800))
                
                ###overwrite pending option to class
                await self.add_pending_options({"channel":ctx.channel.id, "type":'search', "options":likes, "ctx":ctx, "message":options_message},ctx.channel.id)
            
                ###add all reaction options
                reactions = ['1⃣', '2⃣', '3⃣', '4⃣', '5⃣']
                for i in range(len(play_urls)):
                    await options_message.add_reaction(reactions[i])
                await options_message.add_reaction('📻')

    def check_mediator(self, channel_id):
        ###Create mediator object if it does not exist yet
        if not channel_id in self.mediators["channels"]:
            self.mediators["channels"] += [channel_id]
            self.mediators["mediators"] += [mediator(channel_id)]
        
        ###return index
        return self.mediators["channels"].index(channel_id)
    
    async def add_pending_options(self, options_object, message_id):
        if not message_id == self.pending_options["channel"]:
            ###new options message
            self.pending_options = options_object
        else:            
            ###delete previous options message if it exsists (no bugs so far)
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
with open('../dict.json', 'r', encoding='utf8') as dict_file:
    ###read token
    token = json.load(dict_file)["token"]
    
    ###close file
    dict_file.close()
    
###start bot
client = client()
client.run(token)

"""
Known bugs:
"OSError: [WinError 10038] An operation was attempted on something that is not a socket"
"""

"""
To-be-added features:
"""