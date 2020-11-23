'''
Keeps track of a number value for a given discord user, modified through commands.
'''
import os
import json
import discord
from enum import Enum
from inspect import signature
# https://stackoverflow.com/questions/847936/how-can-i-find-the-number-of-arguments-of-a-python-function
# Dumb quirk about the design so far: discordpy stores user id's as ints, but we started interpreting them as strings in the bank dictionary, so weird conversions happen in get_user commands.
class Command(Enum):
    INCREMENT = 100
    DECREMENT = 200
    SET_TO = 300
    GET_BALANCE_SELF = 400
    GET_BALANCE_OTHER = 401
    ALL_BALANCES = 500
    REMOVE_RECORD = 600

class Flag(Enum):
    EVERYONE = 100
    ADMIN_ONLY = 200
    OWNER_ONLY = 284126954918248449

class Bank:
    def __init__(self, client, mongodb, bank_file="bank.log"):
        self.bank = {}
        self.file_to_open = bank_file # deprecated
        self.dir = os.path.dirname(__file__) # absolute dir the script is running in 
        self.money_sign = "$"
        self.mongodb = mongodb
        self.max_money = 9999999999
        self.message_size_limit = 1750
        self.round_money_to_decimal = 2
        self.commands = { # format: "command": [Enum flag, amt of args, permissions required, "help" to display]
            "bill": [Command.INCREMENT, 2, Flag.ADMIN_ONLY, "@user amount"],
            "add": [Command.INCREMENT, 2, Flag.ADMIN_ONLY,"@user amount"],
            "remove": [Command.DECREMENT, 2, Flag.ADMIN_ONLY,"@user amount"],
            "deduct": [Command.DECREMENT, 2, Flag.ADMIN_ONLY,"@user amount"],
            "setbalance": [Command.SET_TO, 2, Flag.ADMIN_ONLY,"@user amount"],
            "set": [Command.SET_TO, 2, Flag.ADMIN_ONLY,"@user amount"],
            "mybalance": [Command.GET_BALANCE_SELF, 0, Flag.EVERYONE,""],
            "balance": [Command.GET_BALANCE_OTHER, 1, Flag.EVERYONE,"@user"],
            "balances": [Command.ALL_BALANCES, 0, Flag.EVERYONE, ""],
            "removeid": [Command.REMOVE_RECORD, 1, Flag.ADMIN_ONLY, "@user"]
        }
    # https://stackoverflow.com/questions/11479816/what-is-the-python-equivalent-for-a-case-switch-statement
    # command is passed in as a pre-parsed list of args, arg[0] being the command
    async def handle_command(self, args, client, client_message):
        options = {
            Command.INCREMENT: self.increment,
            Command.DECREMENT: self.decrement,
            Command.SET_TO: self.set_to,
            Command.GET_BALANCE_SELF: self.get_balance,
            Command.GET_BALANCE_OTHER: self.get_balance,
            Command.ALL_BALANCES: self.all_balances,
            Command.REMOVE_RECORD: self.remove_id
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
            raise Exception("Invalid command for Bank")

    async def initial_bank_load(self):
        # Deprecated - using mongodb should negate the need for file handling like this.
        if os.path.exists(os.path.join(self.dir, self.file_to_open)) and os.path.getsize(os.path.join(self.dir, self.file_to_open)) > 0: # if there's data in there
            bank_file = open(os.path.join(self.dir, self.file_to_open), "r")
            self.bank = json.loads(bank_file.read()) # Json to Dictionary
            bank_file.flush()
            bank_file.close()
            print("Bank loaded!")
        else:
            bank_file = open(os.path.join(self.dir, self.file_to_open), "w")
            bank_file.flush()
            bank_file.close()
            print("Bank() new bank created")
            self.bank = {}

    def write_to_file(self):
        # Deprecated - using mongodb should negate the need for file handling like this.
        bank_file = open(os.path.join(self.dir, self.file_to_open), "w")
        bank_file.write(json.dumps(self.bank)) # not very efficient
        bank_file.flush()
        os.fsync(bank_file.fileno())
        bank_file.close()

    async def increment(self, args, client, client_message):
        userid = str(self.get_user_id_from_message(args[1]))
        amt = abs(float(args[2].replace('\U00002013', '-')))
        guild = str(client_message.guild.id)
        if not isinstance(amt, float):
            raise Exception("Incorrect type for amt") 

        if(client.get_user(int(userid)) != None): # confirm the user is actually existing
            if guild in self.bank and userid in self.bank[guild] and ((self.bank[guild][userid] + amt) <= self.max_money):
                await client_message.add_reaction("\U0001F4B8")
                self.bank[guild][userid] += amt
                self.write_to_file()
            elif guild in self.bank: # guild exists but user does not
                await client_message.add_reaction("\U0001F4B8")
                self.bank[guild][userid] = amt
                self.write_to_file()
                print("created new user in Bank: ", userid, " - ", amt)               
            else:
                await client_message.add_reaction("\U0001F4B8")
                self.bank[guild] = {}
                self.bank[guild][userid] = amt
                self.write_to_file()
                print("created new user in Bank: ", userid, " - ", amt)
        else:
            raise Exception("user doesn't exist")            

    async def decrement(self, args, client, client_message):
        userid = str(self.get_user_id_from_message(args[1]))
        amt = abs(float(args[2].replace('\U00002013', '-')))
        guild = str(client_message.guild.id)
        print("decrement user: ", userid)
        print("decrement amt: ", amt)
        if not isinstance(amt, float):
            raise Exception("Incorrect type for amt")

        if(client.get_user(int(userid)) != None): # confirm the user is actually existing 
            if guild in self.bank and userid in self.bank[guild] and ((self.bank[guild][userid] - amt) >= -self.max_money):
                await client_message.add_reaction("\U0001F4B8")
                self.bank[guild][userid] -= amt
                self.write_to_file()
            elif guild in self.bank: # guild exists but user does not
                await client_message.add_reaction("\U0001F4B8")
                self.bank[guild][userid] = -amt
                self.write_to_file()
                print("created new user in Bank: ", userid, " - ", amt)
            else: # neither exist
                await client_message.add_reaction("\U0001F4B8")
                self.bank[guild] = {}
                self.bank[guild][userid] = -amt
                self.write_to_file()
                print("created new user in Bank: ", userid, " - ", amt)
        else:
            raise Exception("user doesn't exist")

    async def set_to(self, args, client, client_message):
        userid = str(self.get_user_id_from_message(args[1]))
        amt = float(args[2].replace('\U00002013', '-'))
        guild = str(client_message.guild.id)

        if guild in self.bank and userid in self.bank[guild] and ((self.bank[guild][userid] + amt) <= self.max_money) and ((self.bank[guild][userid] + amt) >= -self.max_money):
            self.bank[guild][userid] = amt
        elif guild in self.bank:
            self.bank[guild][userid] = amt
        else:
            self.bank[guild] = {}
            self.bank[guild][userid] = amt
        if not isinstance(amt, float):
            raise Exception("Incorrect type for amt")

        if(client.get_user(int(userid)) != None): # confirm the user is actually existing 
            if amt >= -self.max_money and amt <= self.max_money:
                await client_message.add_reaction("\U0001F4B8")
                self.bank[guild][userid] = amt
                self.write_to_file()
            elif amt <= -self.max_money:
                await client_message.add_reaction("\U0001F4B8")
                self.bank[guild][userid] = -self.max_money
                self.write_to_file()
            elif amt >= self.max_money:
                await client_message.add_reaction("\U0001F4B8")
                self.bank[guild][userid] = self.max_money
                self.write_to_file()
        else:
            raise Exception("user doesn't exist")

    async def get_balance(self, args, client, client_message):
        guild = str(client_message.guild.id)
        if len(args) > 1:
            userid = str(self.get_user_id_from_message(args[1]))
        else:
            userid = str(self.get_user_id_from_message(client_message.author.id))
        print("userid for get_balance: ", userid)
        if guild in self.bank and userid in self.bank[guild]:
            await client_message.channel.send(client.get_user(int(userid)).display_name + "\'s balance is " + self.money_sign + str(format(self.bank[guild][str(userid)], '.'+str(self.round_money_to_decimal)+'f')))
        else:
            raise Exception("user doesn't exist")
    
    async def remove_id(self, args, client, client_message):
        guild = str(client_message.guild.id)
        userid = str(self.get_user_id_from_message(args[1]))
        if guild in self.bank and userid in self.bank[guild]:
            self.bank[guild].pop(userid)
            self.write_to_file()
            await client_message.add_reaction("\U0001F4B8")
        else:
            raise Exception("user doesn't exist")


    async def all_balances(self, args, client, client_message):
        guild = str(client_message.guild.id)
        output = ""
        if guild in self.bank:
            # https://careerkarma.com/blog/python-sort-a-dictionary-by-value/#:~:text=To%20sort%20a%20dictionary%20by%20value%20in%20Python%20you%20can,Dictionaries%20are%20unordered%20data%20structures.
            balances = [list(i) for i in sorted(self.bank[guild].items(), key=lambda x: x[1], reverse=True)]

            for sorted_users in balances:
                username = client.get_user(int(sorted_users[0])).name
                sorted_users[1] = float(sorted_users[1])
                if sorted_users[1] >= self.max_money:
                    sorted_users[1] = self.max_money
                elif sorted_users[1] <= -self.max_money:
                    sorted_users[1] = -self.max_money
                if balances.index(sorted_users) == 0 and len(output) < self.message_size_limit: 
                    output += ("```diff\n- " + username + "\t" + self.money_sign + str(format(sorted_users[1], '.'+str(self.round_money_to_decimal)+'f')) + "\n```") # makes it red (the -)
                elif balances.index(sorted_users) == 1 and len(output) < self.message_size_limit:
                    output += ("```fix\n " + username + "\t" + self.money_sign + str(format(sorted_users[1], '.'+str(self.round_money_to_decimal)+'f')) + "\n```") # makes it yellow
                elif balances.index(sorted_users) == 2 and len(output) < self.message_size_limit:
                    output += ("```fix\n " + username + "\t" + self.money_sign + str(format(sorted_users[1], '.'+str(self.round_money_to_decimal)+'f')) + "\n```") # makes it yellow
                elif len(output) < self.message_size_limit:
                    output += ("```diff\n+ " + username + "\t" + self.money_sign + str(format(sorted_users[1], '.'+str(self.round_money_to_decimal)+'f')) + "\n```") # makes it green
            await client_message.channel.send(output)
        else:
            await client_message.channel.send("No balances yet. Go bill somebody!")

    def get_user_id_from_message(self, msg):
        output = ""
        str_msg = str(msg)
        for char in str_msg:
            if char.isnumeric():
                output = output + char
        print(output)
        return int(output)
