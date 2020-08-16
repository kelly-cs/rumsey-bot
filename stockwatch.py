'''
Keeps track of a stock through tiingo
# https://api.tiingo.com/documentation/general/overview
- set stock alerts when price changes by x percent in 1 day
- get current info on a given stock
'''
import os
import json
import discord
import requests
import asyncio
import time
#from asyncinit import asyncinit
from enum import Enum
from inspect import signature

# TO INSTALL:
# ENTER YOUR TOKEN INTO SELF.TOKEN AND PUT INTO SAME FOLDER AS BOT.PY
# PUT INTO BOT.PY MODULES LIST
# GOOD TO GO!

class Command(Enum):
    WATCH_STOCK_DAILY = 100
    WATCH_STOCK_LONG_TERM = 150
    GET_STOCK_INFO = 200
    SHOW_STOCK_ALERTS = 300
    REMOVE_STOCK_ALERT = 400
    WATCH_CRYPTO_DAILY = 500
    WATCH_CRYPTO_LONG_TERM = 550
    SUBSCRIBE_TO_ALERT = 600

class Flag(Enum):
    EVERYONE = 100
    ADMIN_ONLY = 200
    OWNER_ONLY = 284126954918248449


#@asyncinit
class StockWatch:
    def __init__(self, client, bank = "stock_alert.txt"):
        self.token = "17e85036d317e0f26afe84b4d564312e019b0e82" # ENTER YOUR TIINGO TOKEN HERE AS A STRING https://api.tiingo.com/
        self.client = client
        self.bank = {}
        self.money_sign = "$"
        self.message_size_limit = 1750
        self.length_of_date_string_to_read = 11
        self.file_to_open = bank
        self.dir = os.path.dirname(__file__) # absolute dir the script is running in 
        self.round_money_to_decimal = 2
        self.time_between_requests = 1600
        self.commands = { # format: "command": [Enum flag, amt of args, permissions required, "help" to display]
            "stock": [Command.GET_STOCK_INFO, 1, Flag.EVERYONE, "stock_ticker | return stock price"],
            "getstock": [Command.GET_STOCK_INFO, 1, Flag.EVERYONE, "stock_ticker | return stock price"],
            "stockalertdaily": [Command.WATCH_STOCK_DAILY, 2, Flag.EVERYONE,"(stock_ticker) (percent: 10%) | notifies of stock changes above limit in 1 day"],
            "stockalertlongterm": [Command.WATCH_STOCK_LONG_TERM, 2, Flag.EVERYONE,"(stock_ticker) (percent: 10%) | notifies when stock changes above limit at any time"],
            "removestockalert": [Command.REMOVE_STOCK_ALERT, 1, Flag.EVERYONE,"(stock_ticker) | removes a stock alert"],
            "removestock": [Command.REMOVE_STOCK_ALERT, 1, Flag.EVERYONE,"(stock_ticker) | removes a stock alert"],
            "showalerts": [Command.SHOW_STOCK_ALERTS, 0, Flag.EVERYONE, " show all stock/crypto alerts that are active"],
            "cryptoalertdaily": [Command.WATCH_CRYPTO_DAILY, 3, Flag.EVERYONE,"(exchange [i.e. binance]) (stock_ticker) (percent: 10%) | notifies of stock changes above limit in 1 day"],
            "cryptoalertlongterm": [Command.WATCH_CRYPTO_LONG_TERM, 3, Flag.EVERYONE,"(exchange [i.e. binance]) (stock_ticker) (percent: 10%) | notifies when stock changes above limit at any time"],
            "subscribe": [Command.SUBSCRIBE_TO_ALERT, 1, Flag.EVERYONE,"(stock-ticker) | subscribes to existing stock alert, to be notified"]
        }
    # https://stackoverflow.com/questions/11479816/what-is-the-python-equivalent-for-a-case-switch-statement
    # command is passed in as a pre-parsed list of args, arg[0] being the command
    async def handle_command(self, args, client, client_message):
        options = {
        Command.WATCH_STOCK_DAILY: self.set_stock_alert_daily,
        Command.WATCH_STOCK_LONG_TERM: self.set_stock_alert_long_term,
        Command.GET_STOCK_INFO: self.get_stock_info_and_print,
        Command.SHOW_STOCK_ALERTS: self.show_stock_alerts,
        Command.REMOVE_STOCK_ALERT: self.remove_stock_alert,
        Command.WATCH_CRYPTO_DAILY: self.set_crypto_alert_daily,
        Command.WATCH_CRYPTO_LONG_TERM: self.set_crypto_alert_long_term
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
                raise Exception("Invalid command for StockWatch")

    async def initial_bank_load(self):
        print("Starting initial_bank_load for Stock Alerts..")
        if os.path.exists(os.path.join(self.dir, self.file_to_open)) and os.path.getsize(os.path.join(self.dir, self.file_to_open)) > 0: # if there's data in there
            bank_file = open(os.path.join(self.dir, self.file_to_open), "r")
            self.bank = json.loads(bank_file.read()) # Json to Dictionary
            bank_file.flush()
            bank_file.close()
            print("Stock Alerts loaded!")
            for stocks in self.bank:
                await self.stock_watcher(stocks)
        else:
            bank_file = open(os.path.join(self.dir, self.file_to_open), "w")
            bank_file.flush()
            bank_file.close()
            print("new Stock Alerts bank loaded")
            self.bank = {}
    

    async def write_to_file(self):
        bank_file = open(os.path.join(self.dir, self.file_to_open), "w")
        bank_file.write(json.dumps(self.bank)) # not very efficient
        bank_file.flush()
        os.fsync(bank_file.fileno())
        bank_file.close()

    async def stock_watcher(self, stock):
        print("stock watcher started: " + stock)
        await asyncio.sleep(self.time_between_requests)
        r = await self.get_stock_info([None,stock])
        print("Stock Watcher Routine Call Success: " + stock)
        current_price = float(r[0]["close"])
        previous_close = float(r[0]["open"])
        percent_difference = ((current_price - previous_close) / previous_close) * 100 
        if self.bank[stock]["lastalert"] != r[0]["date"][0:(self.length_of_date_string_to_read-1)] and percent_difference > abs(self.bank[stock]["percent_change"]): # if the change is greater than the alert specification, and it isn't the same time
            await self.print_stock_info(r, self.bank[stock]["channel"], stock, "*24HR Change Alert! [Threshold: " + format(self.bank[stock]["percent_change"]*100, "." + str(self.round_money_to_decimal)+"f") + "%]*")
            self.bank[stock]["lastalert"] = r[0]["date"][0:(self.length_of_date_string_to_read-1)]
            await self.write_to_file()
            await self.stock_watcher(stock)
        else:
            await self.stock_watcher(stock) # keep going and waiting


    async def print_stock_info(self, r, channelid, stock, special_message=None):
        extra_message = ""
        channel = self.client.get_channel(channelid)
        if not special_message == None:
            extra_message = "\n" + special_message
        current_price = float(r[0]["close"])
        previous_close = float(r[0]["open"])
        percent_difference = format(((current_price - previous_close) / previous_close) * 100, "." + str(self.round_money_to_decimal)+"f")
        if current_price <= 0.10 or previous_close <= 0.10:
            round_off_to = 4
        else:
            round_off_to = self.round_money_to_decimal
        if current_price >= previous_close:
            await channel.send(extra_message + "```diff\n+ " + stock + "\t" + ("OPEN: $" + format(previous_close, "." + str(round_off_to)+"f")) +  (" CLOSE: $" + format(current_price, "." + str(round_off_to)+"f") + " (+" + percent_difference + "%) [24h]```")) 
        else:
            await channel.send(extra_message + "```diff\n- " + stock + "\t" + ("OPEN: $" + format(previous_close, "." + str(round_off_to)+"f") )  + (" CLOSE: $" + format(current_price, "." + str(round_off_to)+"f") + " (" + percent_difference + "%) [24h]```")) 
        mention_list = ""
        for subs in self.bank[stock]["subscribers"]:
           mention_list += "<@" + subs + "> "
        await channel.send(mention_list)
    async def get_stock_info(self, args):
        stock = args[1]
        ''' https://finnhub.io/docs/api#quote
        { SAMPLE RESPONSE
            [{"adjClose":0.0021,"adjHigh":0.0024,"adjLow":0.0013,"adjOpen":0.0014,"adjVolume":190908270,
            "close":0.0021,"date":"2020-08-14T00:00:00+00:00","divCash":0.0,"high":0.0024,"low":0.0013,"open":0.0014,"splitFactor":1.0,"volume":190908270}]
            }'''
        api_request = 'https://api.tiingo.com/tiingo/daily/'+ stock +'/prices?token=' + self.token
        print(api_request)
        r = requests.get(api_request)
        r = r.json() # convert to json
        print(r)
        return r
        
    async def get_stock_info_and_print(self, args, client, client_message):
        await self.print_stock_info(self.get_stock_info(args, client, client_message))

    async def set_stock_alert_daily(self, args, client, client_message):
        stock = args[1]
        percent = float(args[2])
        if stock in self.bank and (self.bank[stock]["daily"] != KeyError): # if a daily alert already exists
            raise Exception("A daily alert for " + stock + " already exists!")
        else: # if no alert has been made
            self.bank[stock] = {"daily": 1, "percent_change": percent, "lastalert": 0, "channel": client_message.channel.id, "subscribers": [str(client_message.author.id)]}
            await self.write_to_file()
            await self.stock_watcher(args[1])
    
    async def set_stock_alert_long_term(self, args, client, client_message):
        pass

    async def set_crypto_alert_daily(self, args, client, client_message):
        pass

    async def set_crypto_alert_long_term(self, args, client, client_message):
        pass

    async def remove_stock_alert(self, args, client, client_message):
        pass

    async def show_stock_alerts(self, args, client, client_message):
        pass