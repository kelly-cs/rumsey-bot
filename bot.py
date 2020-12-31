import discord
import sys
import asyncio
import random
import pymongo
import dateutil.parser
from bank import Bank
from stockwatch import StockWatch
from voicealert import VoiceAlert

# To RUN in CMD/Powershell/BASH:
# >> python bot.py your-token-here


client = discord.Client()
delimiter = "$"


# to install a new module, put a comma at the end of the bottom module and insert the call to the new module like Module()
# pass in client
modules = [
    Bank(client),
    StockWatch(client),
    VoiceAlert(client)
]

commands = {}

for mods in modules:
    for args in mods.commands.keys(): # for all commands in the module
        commands[args] = {"nargs": mods.commands[args][1], "module": modules.index(mods), "help": modules[modules.index(mods)].commands[args][3]} # command, amt args, module it belongs to

def get_error_response():
    responses = [
        "come again?",
        "what",
        "?",
        "??",
        "excuse me",
        "uhh"
    ]
    return responses[random.randint(0, len(responses) - 1)]

def get_user_id_from_message(msg):
    output = ""
    for char in msg:
        if char.isnumeric():
            output = output + char
    #print(output)
    return int(output)

def get_help_all():
    output = "```"
    for cmd in commands:
        print(cmd)
        output += "(" + modules[commands[cmd]["module"]].__class__.__name__ + ") " + cmd + " | " + commands[cmd]["help"] + "\n"
    output += "```"
    return output

def get_help_single(cmd):
    return  "```" + cmd + " | " + commands[cmd]["help"] + "\n```" 

# https://discordpy.readthedocs.io/en/latest/quickstart.html
@client.event
async def on_ready():
    print("Logged in as  {0.user}".format(client))
    for mods in modules:
        await mods.initial_bank_load() # initialize all modules

@client.event
async def on_message(message):
    #print(commands)
    if message.author == client.user:
        return

    args = message.content.split()
    if args[0].startswith(delimiter):
        #print(args[0][1:])
        if args[0][1:] == "help" or args[0][1:] == "commands":
            try:
                if len(args) == 1: # list all commands
                    await message.channel.send(get_help_all())
                elif len(args) == 2: # list 1 command
                    await message.channel.send(get_help_single(args[1]))
                else:
                    await message.channel.send(get_error_response())
            except:
                await message.channel.send(get_error_response())
        #elif args[0][1:] == "test_mongo":
        #    await message.channel.send("Temperature at " + "1984-03-05T13:00:00.000+00:00\n" + str(mongodb_client.sample_weatherdata.data.find_one({"ts": dateutil.parser.parse("1984-03-05T13:00:00.000+00:00")})["airTemperature"]["value"]))
        elif args[0][1:] in commands: # remove delimiter and check
            owner_module = commands[args[0][1:]] # index of the owning module
            # print("ARGS GIVEN: ", len(args), "COMMAND ARGS: ", owner_module["nargs"])
            # print("MODULE: ", owner_module["module"])
            if len(args) >= owner_module["nargs"]: # if right number of args
                #try:
                print("about to try: ", args[0])
                await modules[owner_module["module"]].handle_command(args, client, message) # send the whole thing to that module to figure out
                #except Exception as e:
                    #print("error: ", str(e))
                    #await message.channel.send(get_error_response())
    return
    
client.run(sys.argv[1])