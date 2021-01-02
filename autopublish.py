'''
Keeps track of a number value for a given discord user, modified through commands.
'''
import os
import json
import discord
import asyncio
from enum import Enum
from inspect import signature
# https://stackoverflow.com/questions/847936/how-can-i-find-the-number-of-arguments-of-a-python-function
# Dumb quirk about the design so far: discordpy stores user id's as ints, but we started interpreting them as strings in the bank dictionary, so weird conversions happen in get_user commands.
class Command(Enum):
    SET_CHANNEL_TO_AUTOPUBLISH = 100
    ENABLE_AUTOPUBLISH = 200
    DISABLE_AUTOPUBLISH = 201

class Flag(Enum):
    EVERYONE = 100
    ADMIN_ONLY = 200
    OWNER_ONLY = 284126954918248449

class AutoPublish:
    def __init__(self, client, bank_file="autopublish.log"):
        self.dir = os.path.dirname(__file__) # absolute dir the script is running in 
        self.bank = {}
        self.client = client
        self.file_to_open = bank_file
        self.autopublish_enabled = False # loaded from bank
        self.commands = { # format: "command": [Enum flag, amt of args, permissions required, "help" to display]
            "autopublishchannel": [Command.SET_CHANNEL_TO_AUTOPUBLISH, 1, Flag.ADMIN_ONLY, "(announcement channel to autopublish in)"],
            "enableautopublish": [Command.ENABLE_AUTOPUBLISH, 0, Flag.ADMIN_ONLY,"(enable autopublish)"],
            "disableautopublish": [Command.DISABLE_AUTOPUBLISH, 0, Flag.ADMIN_ONLY,"(disable autopublish)"]
        }
    # https://stackoverflow.com/questions/11479816/what-is-the-python-equivalent-for-a-case-switch-statement
    # command is passed in as a pre-parsed list of args, arg[0] being the command
    async def handle_command(self, args, client, client_message):
        options = {
            Command.SET_CHANNEL_TO_AUTOPUBLISH: self.set_channel_to_autopublish,
            Command.ENABLE_AUTOPUBLISH: self.enable_autopublish,
            Command.DISABLE_AUTOPUBLISH: self.disable_autopublish
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
            raise Exception("Invalid command for AutoPublish")

    async def initial_bank_load(self):
        # Deprecated - using mongodb should negate the need for file handling like this.
        if os.path.exists(os.path.join(self.dir, self.file_to_open)) and os.path.getsize(os.path.join(self.dir, self.file_to_open)) > 0: # if there's data in there
            bank_file = open(os.path.join(self.dir, self.file_to_open), "r")
            self.bank = json.loads(bank_file.read()) # Json to Dictionary
            bank_file.flush()
            bank_file.close()
            print("AutoPublish loaded!")
            
        else:
            bank_file = open(os.path.join(self.dir, self.file_to_open), "w")
            bank_file.flush()
            bank_file.close()
            print("AutoPublish new bank created")

        for guilds in self.bank:
            if "autopublish_enabled" in self.bank[guilds] and "autopublish_channel" in self.bank[guilds]:
                if self.bank[guilds]["autopublish_enabled"] == True:
                    print("successfully loaded autopublish for " + str(guilds))
                    asyncio.gather(self.watch_channel_for_updates(self.client.get_channel(int(self.bank[guilds]["autopublish_channel"]))))

    def write_to_file(self):
        # Deprecated - using mongodb should negate the need for file handling like this.
        bank_file = open(os.path.join(self.dir, self.file_to_open), "w")
        bank_file.write(json.dumps(self.bank)) # not very efficient
        bank_file.flush()
        os.fsync(bank_file.fileno())
        bank_file.close()

    async def enable_autopublish(self, args, client, client_message):
        guild = str(client_message.guild.id)
        if guild not in self.bank:
            self.bank[guild] = {}
        else:
            if "autopublish_enabled" in self.bank[guild]:
                if self.bank[guild]["autopublish_enabled"] == True:
                    await client_message.channel.send("Already turned on.")
                else:
                    if "autopublish_channel" in self.bank[guild]:
                        self.bank[guild]["autopublish_enabled"] = True
                        client_message.channel.send("Enabled!")
                        self.write_to_file()
                        await asyncio.gather(self.watch_channel_for_updates(client.get_channel(int(self.bank[guild]["autopublish_channel"])))) # only trigger if it was going from
                    else:
                        await client_message.channel.send("You haven't set a channel yet. Go do that first.")
            else:
                if "autopublish_channel" in self.bank[guild]:
                    self.bank[guild]["autopublish_enabled"] = True
                    self.write_to_file()
                    await asyncio.gather(self.watch_channel_for_updates(client.get_channel(int(self.bank[guild]["autopublish_channel"])))) # only trigger if it was going from 
                else:
                    await client_message.channel.send("Go set a channel first!")

        client_message.channel.send("Autopublish turned on!")
        

    async def disable_autopublish(self, args, client, client_message):
        guild = str(client_message.guild.id)
        if guild not in self.bank:
            self.bank[guild] = {}
        self.bank[guild]["autopublish_enabled"] = False
        client_message.channel.send("Autopublish turned off!")
        self.write_to_file()
        
    # sets the other guilds to notify
    async def set_channel_to_autopublish(self, args, client, client_message):
        guild = str(client_message.guild.id)
        message_channel = self.client.get_channel(client_message.channel.id)
        channelid = args[1] # this will be the id for the channel
        if guild in self.bank:
            self.bank[guild]["autopublish_channel"] = str(self.get_user_id_from_message(channelid))
            await message_channel.send("Autopublish channel set to " + channelid)
        else:
            self.bank[guild] = {}
            self.bank[guild]["autopublish_enabled"] = False
            self.bank[guild]["autopublish_channel"] = str(self.get_user_id_from_message(channelid))
            await message_channel.send("This is a new channel - make sure to manually turn on Autopublish to be activated.")
        self.write_to_file()
    

    # pass in a Channel object, not an id.
    async def watch_channel_for_updates(self, channel):
        #print("Watching " + str(channel.id) + " for voice alert updates.")
        if str(channel.guild.id) not in self.bank:
            self.bank[str(channel.guild.id)] = {}
        if "autopublish_enabled" not in self.bank[str(channel.guild.id)]:
            self.bank[str(channel.guild.id)]["autopublish_enabled"] = False
            print("autopublish not enabled yet. waiting.")
        if self.bank[str(channel.guild.id)]["autopublish_enabled"] == False:
            print("autopublish disabled. turning off updates")
            self.write_to_file()
            return
        async for message in channel.history(limit=1):
            ("publishing " + str(message.content))
            try:
                await message.publish()
            except:
                pass # assumes that it's already published, inefficient and bad mannered but will improve later

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
