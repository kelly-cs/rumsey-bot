import discord
from bank import Bank

client = discord.Client()
bank = Bank()
# https://discordpy.readthedocs.io/en/latest/quickstart.html
@client.event
async def on_ready():
    print("Logged in as  {0.user}".format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if "hello" in message.content:
        await message.channel.send("sup")

client.run('')