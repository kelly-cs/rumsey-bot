import discord
import random
from bank import Bank

client = discord.Client()
bank = Bank()
delimiter = "$"

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
    print(output)
    return int(output)


# https://discordpy.readthedocs.io/en/latest/quickstart.html
@client.event
async def on_ready():
    print("Logged in as  {0.user}".format(client))

@client.event
async def on_message(message):
    args = message.content.split()
    if message.author == client.user:
        return

    '''
    Bank Section

    Commands:
    bill / add @userid amount
    deduct / remove @userid amount
    setbalance @userid amount
    mybalance
    balance @userid
    balances

    '''
    if (args[0].startswith(delimiter+"bill") or args[0].startswith(delimiter+"add")) and len(args) >= 3:
        user = get_user_id_from_message(args[1])
        amt = int(args[2])
        try:
            if(client.get_user(user) != None): # confirm the user is actually existing
                bank.increment(str(user), amt)
                await message.add_reaction("\U0001F4B8")
        except Exception as e:
            print("error: ", str(e))
            await message.channel.send(get_error_response())
            return
        return
    elif (args[0].startswith(delimiter+"deduct") or args[0].startswith(delimiter+"remove")) and len(args) >= 3:
        user = get_user_id_from_message(args[1])
        amt = int(args[2])
        try:
            if(client.get_user(user) != None): # confirm the user is actually existing
                bank.decrement(str(user), amt)
                await message.add_reaction("\U0001F4B8")
        except Exception as e:
            print("error: ", str(e))
            await message.channel.send(get_error_response())
            return
        return
    elif args[0].startswith(delimiter+"setbalance") and len(args) >= 3:
        user = get_user_id_from_message(args[1])
        amt = int(args[2])
        try:
            if(client.get_user(user) != None): # confirm the user is actually existing
                bank.set_to(str(user), amt)
                await message.add_reaction("\U0001F4B8")
        except Exception as e:
            print("error: ", str(e))
            await message.channel.send(get_error_response())
            return
        return       
    elif args[0].startswith(delimiter+"mybalance"):
        user = message.author.id
        try:
            await message.channel.send(client.get_user(user).display_name+ "\'s balance is " + str(bank.get_balance(str(user))))
        except Exception as e:
            print("error: ", str(e))
            await message.channel.send(get_error_response())
            return
        return
    elif args[0].startswith(delimiter+"balance") and len(args) == 2:
        user = get_user_id_from_message(args[1])
        try:
            await message.channel.send(client.get_user(user).display_name + "\'s balance is " + str(bank.get_balance(str(user))))
        except Exception as e:
            print("error: ", str(e))
            await message.channel.send(get_error_response())
            return
        return
    elif args[0].startswith(delimiter+"balances"):
        try:
            await message.channel.send(bank.all_balances(client))
        except Exception as e:
            print("error: ", str(e))
            await message.channel.send(get_error_response())
            return
        return
client.run('')