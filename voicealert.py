'''
Keeps track of a number value for a given discord user, modified through commands.
'''
import os
import json
import discord
import asyncio
from enum import Enum
from inspect import signature
from random import randrange
from gtts import gTTS
# https://stackoverflow.com/questions/847936/how-can-i-find-the-number-of-arguments-of-a-python-function
# Dumb quirk about the design so far: discordpy stores user id's as ints, but we started interpreting them as strings in the bank dictionary, so weird conversions happen in get_user commands.
class Command(Enum):
    ENABLE_RUST_VOICE_ALERT = 100
    DISABLE_RUST_VOICE_ALERT = 101
    MODIFY_VOICE_LANGUAGE = 200
    MODIFY_VOICE_SPEED = 201
    SAY = 300
    SET_ALERT_CHANNEL = 400
    SET_MUSIC = 500
    SHOW_MUSIC_TRACKS = 501

class Flag(Enum):
    EVERYONE = 100
    ADMIN_ONLY = 200
    OWNER_ONLY = 284126954918248449

class VoiceAlert:
    def __init__(self, client, bank_file="voicealert.log"):
        self.dir = os.path.dirname(__file__) # absolute dir the script is running in 
        self.bank = {}
        self.client = client
        self.file_to_open = bank_file
        self.music_directory = "music" # dir where music is stored
        self.music_files = os.listdir(os.path.normpath(self.dir) + "\\" + self.music_directory) # this will also pick up directories. Don't put extra directories here.
        self.voice_alert_channel = "" # loaded from bank
        self.allowed_languages = ["english", "spanish"]
        self.allowed_speeds = ["slow", "normal"]
        self.rust_voice_alert_enabled = False # loaded from bank
        self.music_set = "random" # off, random, 0,1,2,3 for specific songs
        self.voice_speed = "normal" # loaded from bank
        self.voice_language = "english" # loaded from bank
        self.commands = { # format: "command": [Enum flag, amt of args, permissions required, "help" to display]
            "enablerustvoicealert": [Command.ENABLE_RUST_VOICE_ALERT, 0, Flag.ADMIN_ONLY, ""],
            "disablerustvoicealert": [Command.DISABLE_RUST_VOICE_ALERT, 0, Flag.ADMIN_ONLY,""],
            "voicelanguage": [Command.MODIFY_VOICE_LANGUAGE, 1, Flag.ADMIN_ONLY,"(language, ie english)"],
            "voicespeed": [Command.MODIFY_VOICE_SPEED, 1, Flag.ADMIN_ONLY,"(slow|normal)"],
            "say": [Command.SAY, 1, Flag.ADMIN_ONLY,"(text to say)"],
            "setvoicealertchannel": [Command.SET_ALERT_CHANNEL, 1, Flag.ADMIN_ONLY,"(guildids to notify, comma separated)"],
            "voicealertmusic": [Command.SET_MUSIC, 1, Flag.EVERYONE, "(off, random, 0-1-2-3 for specific song)"],
            "showvoicealertsounds": [Command.SHOW_MUSIC_TRACKS, 0, Flag.EVERYONE, ""]
        }
    # https://stackoverflow.com/questions/11479816/what-is-the-python-equivalent-for-a-case-switch-statement
    # command is passed in as a pre-parsed list of args, arg[0] being the command
    async def handle_command(self, args, client, client_message):
        options = {
            Command.ENABLE_RUST_VOICE_ALERT: self.enable_rust_voice_alert,
            Command.DISABLE_RUST_VOICE_ALERT: self.disable_rust_voice_alert,
            Command.MODIFY_VOICE_LANGUAGE: self.modify_voice_language,
            Command.MODIFY_VOICE_SPEED: self.modify_voice_speed,
            Command.SAY: self.say,
            Command.SET_ALERT_CHANNEL: self.set_alert_channel,
            Command.SET_MUSIC: self.set_music,
            Command.SHOW_MUSIC_TRACKS: self.show_music_tracks
        }
        if args[0][1:] in self.commands:
            if self.commands[args[0][1:]][2] == Flag.EVERYONE:
                #print("FUNCTION: ", self.commands[args[0][1:]][0])
                await options[self.commands[args[0][1:]][0]](args, client, client_message) # run the function associated with that command. Grabs enum from self.commands to get function call here.
            elif self.commands[args[0][1:]][2] == Flag.ADMIN_ONLY and client_message.author.guild_permissions.administrator:
                await options[self.commands[args[0][1:]][0]](args, client, client_message) # run the function associated with that command. Grabs enum from self.commands to get function call here.
            elif self.commands[args[0][1:]][2] == Flag.OWNER_ONLY and client_message.author.id == Flag.OWNER_ONLY:
                await options[self.commands[args[0][1:]][0]](args, client, client_message) # run the function associated with that command. Grabs enum from self.commands to get function call here.
        else:
            raise Exception("Invalid command for Voice Alerts")

    async def initial_bank_load(self):
        # Deprecated - using mongodb should negate the need for file handling like this.
        if os.path.exists(os.path.join(self.dir, self.file_to_open)) and os.path.getsize(os.path.join(self.dir, self.file_to_open)) > 0: # if there's data in there
            bank_file = open(os.path.join(self.dir, self.file_to_open), "r")
            self.bank = json.loads(bank_file.read()) # Json to Dictionary
            bank_file.flush()
            bank_file.close()
            print("VoiceAlert loaded!")
            print(self.music_files)
            
        else:
            bank_file = open(os.path.join(self.dir, self.file_to_open), "w")
            bank_file.flush()
            bank_file.close()
            print(self.music_files)
            print("VoiceAlert new bank created")

    def write_to_file(self):
        # Deprecated - using mongodb should negate the need for file handling like this.
        bank_file = open(os.path.join(self.dir, self.file_to_open), "w")
        bank_file.write(json.dumps(self.bank)) # not very efficient
        bank_file.flush()
        os.fsync(bank_file.fileno())
        bank_file.close()

    async def enable_rust_voice_alert(self, args, client, client_message):
        guild = str(client_message.guild.id)
        if guild not in self.bank:
            self.bank[guild] = {}
        self.bank[guild]["rust_voice_alert_enabled"] = True
        self.write_to_file()
        if "set_alert_channel" in self.bank[guild]:
            alert_channel = client.get_channel(int(self.bank[guild]["set_alert_channel"]))
            await self.watch_channel_for_updates(alert_channel)
            await client_message.channel.send("Got it. Voice alerts enabled on " + alert_channel.name)
        else:
            await client_message.channel.send("You haven't set an alert channel to watch yet. Try that first.")

    async def disable_rust_voice_alert(self, args, client, client_message):
        guild = str(client_message.guild.id)
        if guild not in self.bank:
            self.bank[guild] = {}
        self.bank[guild]["rust_voice_alert_enabled"] = False
        self.write_to_file()
        
    async def modify_voice_language(self, args, client, client_message):
        guild = str(client_message.guild.id)
        if guild not in self.bank:
            self.bank[guild] = {}
        if self.bank[guild]["voice_language"] != args[1] and args[1] in self.allowed_languages: # if the language is different than specified in the command
            self.bank[guild]["voice_language"] = args[1]
            self.write_to_file()

    async def modify_voice_speed(self, args, client, client_message):
        guild = str(client_message.guild.id)
        if guild not in self.bank:
            self.bank[guild] = {}
        if self.bank[guild]["voice_speed"] != args[1] and args[1] in self.allowed_speeds: # if the speed is different than specified in the command
            self.voice_language = args[1]
            self.bank[guild]["voice_speed"] = args[1]
            self.write_to_file()

    async def music_set(self, args, client, client_message):
        guild = str(client_message.guild.id)
        if guild not in self.bank:
            self.bank[guild] = {}
        if self.bank[guild]["current_song"] != args[1] and (args[1] == "off" or args[1] == "random" or args[1] < len(self.music_files)):
            self.bank[guild]["current_song"] = args[1]
            self.write_to_file()

    # https://stackoverflow.com/questions/62494399/how-to-play-gtts-mp3-file-in-discord-voice-channel-the-user-is-in-discord-py
    async def say(self, args, client, client_message, channel_to_join=None):
        guild = "" 
        tts_message = ""
        if channel_to_join != None:
            if channel_to_join.type == discord.ChannelType.voice:
                guild = str(channel_to_join.guild.id)
                channel_to_join = channel_to_join # assume it's a channel
                tts_message = str(client_message)
        else:
            guild = str(client_message.guild.id)
            member = client_message.author # get the member object from msg
            channel_to_join = member.voice.channel # get the VoiceChannel object from Member.voice object
            tts_message = client_message.content[4:] # remove this magic number later..
        tts = gTTS(text=tts_message, lang="en") # make this support other languages later
        try:
            os.remove(self.dir + "\\" + guild + ".mp3")
        except:
            pass
        tts.save(guild + ".mp3")
        #try:
        if channel_to_join != None:
            vc = await channel_to_join.connect() # join the channel, returns VoiceClient
            try:
                music_to_play = self.bank[guild][current_song] # get current song setting for this channel
            except:
                music_to_play = "random"
            try:
                if music_to_play != "off":
                    if music_to_play == "random":
                        song_to_select = randrange(len(self.music_files))
                        await vc.play(discord.FFmpegPCMAudio(self.music_directory + "\\" + self.music_files[song_to_select])) # random song
                        vc.source = discord.PCMVolumeTransformer(vc.source)
                        vc.source.volume = 1 # 0 to 1
                    else: # assume it is an integer, could be a security issue
                        await vc.play(discord.FFmpegPCMAudio(self.music_directory + "\\" + self.music_files[music_to_play])) # specific song
                        vc.source = discord.PCMVolumeTransformer(vc.source)
                        vc.source.volume = 1 # 0 to 1
            except: # this is shitty and here to just keep the code working
                pass
            print("about to play tts: " + guild)
            while vc.is_playing():
                await asyncio.sleep(0.25)
            try:
                await vc.play(discord.FFmpegPCMAudio(guild + ".mp3")) # this is the tts
            except:
                pass
            while vc.is_playing():
                await asyncio.sleep(1)
            await vc.disconnect()
            try:
                os.remove(self.dir + "\\" + guild + ".mp3")
            except:
                print("couldnt remove " + self.dir + "\\" + guild + ".mp3")

        # Handle the exceptions that can occur
        #except Exception as e:
        #    await client_message.channel.send("VoiceAlert is dying: " + str(e))
            
        
    # sets the other guilds to notify
    async def set_alert_channel(self, args, client, client_message):
        guild = str(client_message.guild.id)
        message_channel = self.client.get_channel(client_message.channel.id)
        channelid = args[1] # this will be the id for the channel
        if guild in self.bank:
            self.bank[guild]["set_alert_channel"] = str(self.get_user_id_from_message(channelid))
            if "last_alert_message" not in self.bank[guild]: # if no alert has been triggered yet
                self.bank[guild]["last_alert_message"] = "none"
            if "rust_voice_alert_enabled" not in self.bank[guild]: # if no alert has been triggered yet
                self.bank[guild]["rust_voice_alert_enabled"] = False
        else:
            self.bank[guild] = {}
            self.bank[guild]["last_alert_message"] = "none"
            self.bank[guild]["rust_voice_alert_enabled"] = False
            self.bank[guild]["set_alert_channel"] = str(self.get_user_id_from_message(channelid))
            await message_channel.send("This is a new channel - make sure to manually turn on Rust voice alerts to be activated.")
        self.write_to_file()
        
        alert_channel = self.client.get_channel(int(self.get_user_id_from_message(channelid)))
        await message_channel.send("I'll watch " + alert_channel.name + " for updates.")
        await asyncio.gather(self.watch_channel_for_updates(alert_channel))
        

    # pass in a Guild object, not a guildid!
    # returns a VoiceChannel
    async def get_most_populated_channel_in_guild(self, guild):
        most_populated_channel = "None"
        largest_amt_users = 0
        for channel in guild.channels: # returns a generator, so it works like a for loop.
            if channel.type == discord.ChannelType.voice:
                if len(channel.members) > 0 and len(channel.members) > largest_amt_users:
                    most_populated_channel = channel
                    largest_amt_users = len(channel.members)
        return most_populated_channel

    async def set_music(self, args, client, client_message):
        guild = str(client_message.guild.id)
        channel = self.client.get_channel(client_message.channel.id)
        music_id = 0
        if guild not in self.bank:
            self.bank[guild] = {}
        if args[1] == "off":
            self.bank[guild]["set_music"] = "off"
            await channel.send("Set the alert sound to: off")
        elif args[1] == "random":
            self.bank[guild]["set_music"] = "random"
            await channel.send("Set the alert sound to: random")
        elif args[1].isnumeric():
            music_id = int(args[1]) # this will be the id for the channel
            self.bank[guild]["set_music"] = music_id
            await channel.send("Set the alert sound to: " + str(music_id) + " - " + self.music_files[music_id])
        else:
            await channel.send("You screwed that up somehow")
            return
        self.write_to_file()
        
        

    async def show_music_tracks(self, args, client, client_message):
        output = ""
        index = 0
        for songs in self.music_files:
            output += str(index) + " - " + songs + "\n"
            index += 1
        channel = self.client.get_channel(client_message.channel.id)
        await channel.send(output)


    # right now, the "trigger" will simply be listening to a discord channel for new messages.
    # these messages are assumed to come from a webhook where the rust notifications come from.
    # we can add fancier ways of triggering this later, like sending http requests over the network
    # but right now I don't care
    async def trigger_alert(self, message_to_say, guilds_to_join):
        print("triggering voice alert")
        voice_channel_to_join = await self.get_most_populated_channel_in_guild(guilds_to_join)
        await self.say(message_to_say, self.client, message_to_say, voice_channel_to_join)

    # pass in a Channel object, not an id.
    async def watch_channel_for_updates(self, channel):
        #print("Watching " + str(channel.id) + " for voice alert updates.")
        if self.bank[str(channel.guild.id)]["rust_voice_alert_enabled"] == False:
            return
        async for message in channel.history(limit=1):
            print(message.content)
            if message.id != self.bank[str(channel.guild.id)]["last_alert_message"]: # if the id is different it's a new message - this is inefficient, but due to how i handle messages in bot.py.
                await self.trigger_alert(message.content, message.guild)
                self.bank[str(channel.guild.id)]["last_alert_message"] = message.id
                self.write_to_file()

        await asyncio.sleep(5)
        await asyncio.gather(self.watch_channel_for_updates(channel))

    def get_user_id_from_message(self, msg):
        output = ""
        str_msg = str(msg)
        for char in str_msg:
            if char.isnumeric():
                output = output + char
        print(output)
        return int(output)
