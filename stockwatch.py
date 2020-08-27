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
from enum import Enum
from inspect import signature

# TO INSTALL:
# ENTER YOUR TOKEN INTO SELF.TOKEN AND PUT INTO SAME FOLDER AS BOT.PY
# PUT INTO BOT.PY MODULES LIST
# GOOD TO GO!

class Command(Enum):
    WATCH_STOCK_DAILY = 100
    WATCH_STOCK_LONG_TERM = 150
    WATCH_CRYPTO_DAILY = 160
    WATCH_CRYPTO_LONG_TERM = 170
    GET_STOCK_INFO = 200
    GET_CRYPTO_INFO = 250
    SHOW_ALERTS = 300
    SHOW_SUBSCRIBERS = 350
    REMOVE_STOCK_ALERT_DAILY = 400
    REMOVE_STOCK_ALERT_LONG_TERM = 450
    REMOVE_CRYPTO_ALERT_DAILY = 460
    REMOVE_CRYPTO_ALERT_LONG_TERM = 470

    SUBSCRIBE_TO_ALERT = 600
    UNSUBSCRIBE_TO_ALERT = 601
    LIST_SUBSCRIBERS = 700

class Flag(Enum):
    EVERYONE = 100
    ADMIN_ONLY = 200
    OWNER_ONLY = 284126954918248449


class StockWatch:
    def __init__(self, client, bank = "stock_alert.txt"):
        self.token = "" # ENTER YOUR TIINGO TOKEN HERE AS A STRING https://api.tiingo.com/
        self.current_watchers = 0
        self.watch_limit_per_server = 20
        self.watch_limit_all_servers = 100
        self.client = client
        self.bank = {}
        self.money_sign = "$"
        self.message_size_limit = 1750
        self.length_of_date_string_to_read = 11
        self.file_to_open = bank
        self.dir = os.path.dirname(__file__) # absolute dir the script is running in 
        self.round_money_to_decimal = 2
        self.time_between_requests = 1800
        self.commands = { # format: "command": [Enum flag, amt of args, permissions required, "help" to display]
            "stock": [Command.GET_STOCK_INFO, 1, Flag.EVERYONE, "ticker | return stock price"],
            "getstock": [Command.GET_STOCK_INFO, 1, Flag.EVERYONE, "ticker | return stock price"],
            "getcrypto": [Command.GET_CRYPTO_INFO, 1, Flag.EVERYONE, "ticker | return crypto price [format: btcusd]"],
            "stockalertdaily": [Command.WATCH_STOCK_DAILY, 2, Flag.EVERYONE,"ticker (percent: 0.10) | notifies of stock changes above limit in 1 day"],
            "stockalertlongterm": [Command.WATCH_STOCK_LONG_TERM, 2, Flag.EVERYONE,"ticker (percent: 0.10) | notifies when stock changes above limit at any time"],
            "removestockalertdaily": [Command.REMOVE_STOCK_ALERT_DAILY, 1, Flag.EVERYONE,"ticker | removes a stock alert"],
            "removestockalertlongterm": [Command.REMOVE_STOCK_ALERT_LONG_TERM, 1, Flag.EVERYONE,"ticker | removes a stock alert"],
            "showalerts": [Command.SHOW_ALERTS, 0, Flag.EVERYONE, " show all stock/crypto alerts that are active"],
            "cryptoalertdaily": [Command.WATCH_CRYPTO_DAILY, 2, Flag.EVERYONE," ticker (percent: 0.10) | notifies of crypto changes above limit in 1 day"],
            "cryptoalertlongterm": [Command.WATCH_CRYPTO_LONG_TERM, 2, Flag.EVERYONE,"ticker (percent: 0.10) | notifies when crypto changes above limit at any time"],
            "removecryptoalertdaily": [Command.REMOVE_CRYPTO_ALERT_DAILY, 1, Flag.EVERYONE,"ticker | removes a crypto alert"],
            "removecryptoalertlongterm": [Command.REMOVE_CRYPTO_ALERT_LONG_TERM, 1, Flag.EVERYONE,"ticker | removes a crypto alert"],
            "subscribe": [Command.SUBSCRIBE_TO_ALERT, 1, Flag.EVERYONE,"ticker | subscribes to existing stock alert, to be notified"],
            "unsubscribe": [Command.UNSUBSCRIBE_TO_ALERT, 1, Flag.EVERYONE,"ticker | unsubscribes from an existing stock alert"],
            "subscribers": [Command.LIST_SUBSCRIBERS, 1, Flag.EVERYONE,"ticker | lists all people subscribed to stock alert"]
        }

    # https://stackoverflow.com/questions/11479816/what-is-the-python-equivalent-for-a-case-switch-statement
    # command is passed in as a pre-parsed list of args, arg[0] being the command
    async def handle_command(self, args, client, client_message):
        options = {
        Command.WATCH_STOCK_DAILY: self.set_stock_alert_daily,
        Command.WATCH_STOCK_LONG_TERM: self.set_stock_alert_long_term,
        Command.GET_CRYPTO_INFO: self.get_crypto_info_and_print,
        Command.GET_STOCK_INFO: self.get_stock_info_and_print,
        Command.SHOW_ALERTS: self.show_alerts,
        Command.REMOVE_STOCK_ALERT_DAILY: self.remove_stock_alert_daily,
        Command.REMOVE_STOCK_ALERT_LONG_TERM: self.remove_stock_alert_long_term,
        Command.REMOVE_CRYPTO_ALERT_DAILY: self.remove_crypto_alert_daily,
        Command.REMOVE_CRYPTO_ALERT_LONG_TERM: self.remove_crypto_alert_long_term,
        Command.WATCH_CRYPTO_DAILY: self.set_crypto_alert_daily,
        Command.WATCH_CRYPTO_LONG_TERM: self.set_crypto_alert_long_term,
        Command.SUBSCRIBE_TO_ALERT: self.subscribe_to_alert,
        Command.UNSUBSCRIBE_TO_ALERT: self.unsubscribe_to_alert,
        Command.LIST_SUBSCRIBERS: self.list_subscribers
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
            for guilds in self.bank:
                for stocks in self.bank[guilds]:
                    if self.current_watchers < self.watch_limit_all_servers:
                        self.current_watchers += 1
                        if self.bank[guilds][stocks]["type"] == "stock":
                            if self.bank[guilds][stocks]["daily"] == 1:
                                asyncio.gather( self.stock_watcher_daily(stocks, guilds))
                            if self.bank[guilds][stocks]["long_term"] == 1:
                                asyncio.gather(self.stock_watcher_long_term(stocks, guilds))
                        elif self.bank[guilds][stocks]["type"] == "crypto":
                            if self.bank[guilds][stocks]["daily"] == 1:
                                asyncio.gather(self.crypto_watcher_daily(stocks, guilds))
                            if self.bank[guilds][stocks]["long_term"] == 1:
                                asyncio.gather(self.crypto_watcher_long_term(stocks, guilds))

        else:
            bank_file = open(os.path.join(self.dir, self.file_to_open), "w")
            bank_file.flush()
            bank_file.close()
            print("new Stock Alerts bank loaded")
            self.bank = {}
    

    def write_to_file(self):
        bank_file = open(os.path.join(self.dir, self.file_to_open), "w")
        bank_file.write(json.dumps(self.bank)) # not very efficient
        bank_file.flush()
        os.fsync(bank_file.fileno())
        bank_file.close()

    async def stock_watcher_daily(self, stock, guild):
        print("stock watcher daily started: " + stock)
        if stock in self.bank[guild] and self.bank[guild][stock]["daily"] == 1: # double check to make sure an alert exists
            await asyncio.sleep(self.time_between_requests)
            r = await self.get_stock_info([None,stock])
            print("Stock Watcher Daily Routine Call Success: " + stock)
            current_price = float(r[0]["close"])
            previous_close = float(r[0]["open"])
            percent_difference = ((current_price - previous_close) / previous_close)
            if self.bank[guild][stock]["daily_lastalert"] != r[0]["date"][0:(self.length_of_date_string_to_read-1)] and abs(percent_difference) > abs(self.bank[guild][stock]["daily_percent_change"]): # if the change is greater than the alert specification, and it isn't the same time
                self.bank[guild][stock]["daily_lastalert"] = r[0]["date"][0:(self.length_of_date_string_to_read-1)]
                self.write_to_file()
                await self.print_stock_info(r, guild, self.bank[guild][stock]["channel"], stock, True, "*24HR Change Alert! [Threshold: " + format(self.bank[guild][stock]["daily_percent_change"]*100, "." + str(self.round_money_to_decimal)+"f") + "%]*")
                await asyncio.gather(await self.stock_watcher_daily(stock, guild))
            else:
                await asyncio.gather(await self.stock_watcher_daily(stock, guild))
        else:
            print('ending stockwatcherdaily thread')
            return # this will end the thread for us


    async def print_stock_info(self, r, guild, channelid, stock, alert_subscribers, special_message=None):
        extra_message = ""
        channel = self.client.get_channel(channelid)
        print("TRYING TO PRINT STOCK " + stock + " IN CHANNEL " + str(channelid))
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
        if alert_subscribers == True:
            for subs in self.bank[guild][stock]["subscribers"]:
                mention_list += "<@" + subs + "> "
            await channel.send(mention_list)

        else:
            print("No subscribers detected for " + stock)
        

    async def get_stock_info(self, args):
        stock = args[1]
        ''' TIINGO
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
        stock = args[1] # returns stock name as string
        guild = str(client_message.guild.id)
        channel = client_message.channel.id
        await self.print_stock_info(await self.get_stock_info(args), guild, channel, stock, False)

    async def set_stock_alert_daily(self, args, client, client_message):
        try:
            stock = args[1]
            percent = float(args[2])
            guild = str(client_message.guild.id)
            if guild in self.bank and stock in self.bank[guild] and (self.bank[guild][stock]["daily"] == 1): # if a daily alert already exists
                await client_message.channel.send("A daily alert already exists for " + stock + " -  remove it first!")
                raise Exception("A daily alert for " + stock + " already exists!")
            elif guild in self.bank and stock in self.bank[guild]: # if the stock is in the system, probably as a long term alert, don't delete it!
                self.bank[guild][stock]["daily"] = 1
                self.bank[guild][stock]["daily_lastalert"] = 0
                self.bank[guild][stock]["daily_percent_change"] = percent
                self.bank[guild][stock]["channel"] = client_message.channel.id # yes - this will overwrite whatever the other setting makes (daily will overwrite long, and so forth). can fix later.
                if str(client_message.author.id) not in self.bank[guild][stock]["subscribers"]: # don't destroy the subscriber list. yes, we should probably make a separate list for short vs long term later.
                    self.bank[guild][stock]["subscribers"].append(str(client_message.author.id)) # if already subscribed, do nothing.
                self.write_to_file()
                await client_message.add_reaction("\U00002611")
                await asyncio.gather(self.stock_watcher_daily(stock, guild))
            elif guild in self.bank: # guild exists but alert does not
                self.bank[guild][stock] = {"daily": 1, "long_term":0, "daily_percent_change": percent, "long_term_percent_change": 0,"long_term_initial_amount":0,  "daily_lastalert": 0, "long_term_lastalert":0, "channel": client_message.channel.id, "subscribers": [str(client_message.author.id)], "type": "stock"}
                self.write_to_file()
                await client_message.add_reaction("\U00002611")
                await asyncio.gather(self.stock_watcher_daily(stock, guild))
            else: # if no alert has been made
                self.bank[guild] = {}
                self.bank[guild][stock] = {"daily": 1, "long_term":0, "daily_percent_change": percent, "long_term_percent_change": 0, "long_term_initial_amount":0, "daily_lastalert": 0, "long_term_lastalert":0, "channel": client_message.channel.id, "subscribers": [str(client_message.author.id)], "type": "stock"}
                self.write_to_file()
                await client_message.add_reaction("\U00002611")
                await asyncio.gather(self.stock_watcher_daily(stock, guild))
        except:
            await client_message.channel.send("Something weird with the formatting there. Try again")

    async def set_stock_alert_long_term(self, args, client, client_message):
        #try:
        stock = args[1] # stock name
        percent = float(args[2]) # amt of percent change to watch for
        r = await self.get_stock_info(args)
        initial_amount = float(r[0]["close"]) # gets the entry position
        guild = str(client_message.guild.id)
        if guild in self.bank and stock in self.bank[guild] and self.bank[guild][stock]["long_term"] == 1: # if a long term alert already exists
            await client_message.channel.send("A long term alert already exists for " + stock + " at " + self.bank[guild][stock]["long_term_initial_amount"] + " +/- " + self.bank[guild][stock]["long_term_percent_change"] + "%" + " - remove that first!")
            raise Exception("A long term alert already exists for " + stock + " at " + self.bank[guild][stock]["long_term_initial_amount"] + " +/- " + self.bank[guild][stock]["long_term_percent_change"] + "%")
        elif guild in self.bank and stock in self.bank[guild]: # if the stock is in the system, probably as a daily alert, don't delete it!
            self.bank[guild][stock]["long_term"] = 1
            self.bank[guild][stock]["long_term_lastalert"] = 0
            self.bank[guild][stock]["long_term_initial_amount"] = initial_amount
            self.bank[guild][stock]["long_term_percent_change"] = percent
            self.bank[guild][stock]["channel"] = client_message.channel.id # yes - this will overwrite whatever the other setting makes (daily will overwrite long, and so forth). can fix later.
            if str(client_message.author.id) not in self.bank[guild][stock]["subscribers"]: # don't destroy the subscriber list. yes, we should probably make a separate list for short vs long term later.
                self.bank[guild][stock]["subscribers"].append(str(client_message.author.id)) # if already subscribed, do nothing.
            self.write_to_file()
            await client_message.add_reaction("\U00002611")
            await asyncio.gather(self.stock_watcher_long_term(stock, guild))
        elif guild in self.bank: # if guild exists but alert does not:
            self.bank[guild][stock] = {"daily": 0, "long_term":1, "daily_percent_change": 0, "long_term_percent_change": percent,"long_term_initial_amount":initial_amount,  "daily_lastalert": 0, "long_term_lastalert":0, "channel": client_message.channel.id, "subscribers": [str(client_message.author.id)], "type": "stock"}
            self.write_to_file()
            await client_message.add_reaction("\U00002611")
            await asyncio.gather(self.stock_watcher_long_term(stock, guild))
        else: # guild does not exist and neither does alert
            self.bank[guild] = {}
            self.bank[guild][stock] = {"daily": 0, "long_term":1, "daily_percent_change": 0, "long_term_percent_change": percent, "long_term_initial_amount":initial_amount, "daily_lastalert": 0, "long_term_lastalert":0, "channel": client_message.channel.id, "subscribers": [str(client_message.author.id)], "type": "stock"}
            self.write_to_file()
            await client_message.add_reaction("\U00002611")
            await asyncio.gather(self.stock_watcher_long_term(stock, guild))

    async def crypto_watcher_daily(self, crypto, guild):
        print("crypto watcher daily started: " + crypto)
        if guild in self.bank and crypto in self.bank[guild] and self.bank[guild][crypto]["daily"] == 1: # double check to make sure an alert exists
            await asyncio.sleep(self.time_between_requests)
            r = await self.get_crypto_info([None,crypto])
            print("crypto Watcher daily Routine Call Success: " + crypto)
            current_price = float(r[0]["priceData"][-1]["close"]) # get the last (most recent price) for the day
            previous_close = float(r[0]["priceData"][0]["open"]) # get the first (midnight today price) for the day
            percent_difference = ((current_price - previous_close) / previous_close)
            if self.bank[guild][crypto]["daily_lastalert"] != r[0]["priceData"][-1]["date"][0:(self.length_of_date_string_to_read-1)] and abs(percent_difference) > abs(self.bank[guild][crypto]["daily_percent_change"]): # if the change is greater than the alert specification, and it isn't the same time
                self.bank[guild][crypto]["daily_lastalert"] = r[0]["priceData"][-1]["date"][0:(self.length_of_date_string_to_read-1)]
                self.write_to_file()
                await self.print_crypto_info(r, guild,  self.bank[guild][crypto]["channel"], crypto, True, "*24HR Change Alert! [Threshold: " + format(self.bank[guild][crypto]["daily_percent_change"]*100, "." + str(self.round_money_to_decimal)+"f") + "%]*")
                await asyncio.gather(self.crypto_watcher_daily(crypto, guild))
            else:
                await asyncio.gather(self.crypto_watcher_daily(crypto, guild))
        else: 
            print('ending cryptowatchdaily thread: ' + crypto)
            return # this will end the thread for us

    async def crypto_watcher_long_term(self, crypto, guild):
        print("crypto watcher long_term started: " + crypto)
        if guild in self.bank and crypto in self.bank[guild] and self.bank[guild][crypto]["long_term"] == 1: # double check to make sure an alert exists
            await asyncio.sleep(self.time_between_requests)
            r = await self.get_crypto_info([None,crypto])
            print("crypto Watcher daily Routine Call Success: " + crypto)
            current_price = float(r[0]["priceData"][-1]["close"]) # get the last (most recent price) for the day
            previous_close = self.bank[guild][stock]["long_term_initial_amount"] # get the first (midnight today price) for the day
            percent_difference = ((current_price - previous_close) / previous_close)
            if self.bank[guild][crypto]["long_term_lastalert"] != r[0]["priceData"][-1]["date"][0:(self.length_of_date_string_to_read-1)] and abs(percent_difference) > abs(self.bank[guild][crypto]["long_term_percent_change"]): # if the change is greater than the alert specification, and it isn't the same time
                self.bank[guild][crypto]["long_term_lastalert"] = r[0]["priceData"][-1]["date"][0:(self.length_of_date_string_to_read-1)]
                await self.print_crypto_info(r, guild,  self.bank[guild][crypto]["channel"], crypto, True, "*Long Term Change Alert! [Threshold: " + format(self.bank[guild][crypto]["long_term_percent_change"]*100, "." + str(self.round_money_to_decimal)+"f") + "%] - Entry: $" + self.bank[guild][crypto]["long_term_initial_amount"]+ " *")
                self.bank[guild][crypto]["long_term"] = 0
                self.bank[guild][crypto]["long_term_initial_amount"] = 0 # delete long term alert after it is tripped.
                self.write_to_file()
                await asyncio.gather(self.crypto_watcher_long_term(crypto, guild))
            else:
                await asyncio.gather(self.crypto_watcher_long_term(crypto, guild))
        else: 
            print('ending cryptowatch long_term thread: ' + crypto)
            return # this will end the thread for us

    async def stock_watcher_long_term(self, stock, guild):
        print("stock watcher long_term started: " + stock)
        if guild in self.bank and stock in self.bank[guild] and self.bank[guild][stock]["long_term"] == 1: # double check to make sure an alert exists
            await asyncio.sleep(self.time_between_requests)
            r = await self.get_stock_info([None,stock])
            print("stock Watcher daily Routine Call Success: " + stock)
            current_price = float(r[0]["close"])
            previous_close = self.bank[guild][stock]["long_term_initial_amount"]
            percent_difference = ((current_price - previous_close) / previous_close)
            if self.bank[guild][stock]["long_term_lastalert"] != r[0]["date"][0:(self.length_of_date_string_to_read-1)] and abs(percent_difference) > abs(self.bank[guild][stock]["long_term_percent_change"]): # if the change is greater than the alert specification, and it isn't the same time
                self.bank[guild][stock]["long_term_lastalert"] = r[0]["date"][0:(self.length_of_date_string_to_read-1)]
                await self.print_stock_info(r, guild,  self.bank[guild][stock]["channel"], stock, True, "*Long Term Change Alert! [Threshold: " + format(self.bank[guild][stock]["long_term_percent_change"]*100, "." + str(self.round_money_to_decimal)+"f") + "%] - Entry: $" + self.bank[guild][stock]["long_term_initial_amount"]+ " *")
                self.bank[guild][stock]["long_term"] = 0
                self.bank[guild][stock]["long_term_initial_amount"] = 0 # delete long term alert after it is tripped.
                self.write_to_file()
                await asyncio.gather(self.stock_watcher_long_term(stock, guild))
            else:
                await asyncio.gather(self.stock_watcher_long_term(stock, guild))
        else: 
            print('ending stockwatch long_term thread: ' + stock)
            return # this will end the thread for us

    async def get_crypto_info(self, args):
        crypto = args[1]
        ''' https://api.tiingo.com/tiingo/crypto/top?tickers=btcusd
        { SAMPLE RESPONSE
        [{"ticker": "btcusd", "baseCurrency": "btc", "quoteCurrency": "usd", "topOfBookData": [{"bidPrice": 11869.0, "lastPrice": 11854.25, "quoteTimestamp": "2020-08-16T21:57:22.989901+00:00",
        "bidExchange": "BITFINEX", "bidSize": 0.21862052, "lastSize": 0.011224, "askSize": 0.043, "lastSizeNotional": 133.052102, "askExchange": "BIBOX", "askPrice": 5365.6811, "lastSaleTimestamp": "2020-08-16T21:57:23.257000+00:00", "lastExchange": "BINANCE"}]}]
            }'''
        api_request = 'https://api.tiingo.com/tiingo/crypto/prices?tickers='+ crypto +'&token=' + self.token
        print(api_request)
        r = requests.get(api_request)
        r = r.json() # convert to json
        print(r)
        return r


    async def print_crypto_info(self, r, guild, channelid, crypto, alert_subscribers, special_message=None):
        extra_message = ""
        print("TRYING TO PRINT CRYPTO " + crypto + " IN CHANNEL " + str(channelid))
        channel = self.client.get_channel(channelid)
        try:
            if not special_message == None:
                extra_message = "\n" + special_message
            current_price = float(r[0]["priceData"][-1]["close"]) # get the last (most recent price) for the day
            previous_close = float(r[0]["priceData"][0]["open"]) # get the first (midnight today price) for the day
            percent_difference = format(((current_price - previous_close) / previous_close) * 100, "." + str(self.round_money_to_decimal)+"f")
            if current_price <= 0.10 or previous_close <= 0.10:
                round_off_to = 8
            else:
                round_off_to = self.round_money_to_decimal
            if current_price >= previous_close:
                await channel.send(extra_message + "```diff\n+ " + crypto + "\t" + ("OPEN: " + format(previous_close, "." + str(round_off_to)+"f")) +  (" CURRENT: " + format(current_price, "." + str(round_off_to)+"f") + " (+" + percent_difference + "%) [24h]```")) 
            else:
                await channel.send(extra_message + "```diff\n- " + crypto + "\t" + ("OPEN: " + format(previous_close, "." + str(round_off_to)+"f") )  + (" CURRENT: " + format(current_price, "." + str(round_off_to)+"f") + " (" + percent_difference + "%) [24h]```")) 
        except:
            await channel.send("Don't see " + crypto + " on the exchange. Maybe try wording it another way?")

        mention_list = ""
        if alert_subscribers == True:
            for subs in self.bank[str(guild)][crypto]["subscribers"]:
                mention_list += "<@" + subs + "> "
            await channel.send(mention_list)

    async def get_crypto_info_and_print(self, args, client, client_message):
        crypto = args[1] # returns stock name as string
        channel = client_message.channel.id
        guild = str(client_message.guild.id)
        await self.print_crypto_info(await self.get_crypto_info(args), guild, channel, crypto, False)
       
    async def set_crypto_alert_daily(self, args, client, client_message):
        crypto = args[1]
        percent = float(args[2])
        guild = str(client_message.guild.id)
        
        try:
            if guild in self.bank and crypto in self.bank[guild] and (self.bank[guild][crypto]["daily"] == 1): # if a daily alert already exists
                await client_message.channel.send("A daily alert already exists for " + crypto + " -  remove it first!")
                raise Exception("A daily alert for " + crypto + " already exists!")
            elif guild in self.bank and crypto in self.bank[guild]: # if the crypto is in the system, don't delete it!
                self.bank[guild][crypto]["daily"] = 1
                self.bank[guild][crypto]["daily_lastalert"] = 0
                self.bank[guild][crypto]["daily_percent_change"] = percent
                self.bank[guild][crypto]["channel"] = client_message.channel.id # yes - this will overwrite whatever the other setting makes (daily will overwrite long, and so forth). can fix later.
                if str(client_message.author.id) not in self.bank[guild][crypto]["subscribers"]: # don't destroy the subscriber list. yes, we should probably make a separate list for short vs long term later.
                    self.bank[guild][crypto]["subscribers"].append(str(client_message.author.id)) # if already subscribed, do nothing.
                self.write_to_file()
                await client_message.add_reaction("\U00002611")
                await asyncio.gather(self.crypto_watcher_daily(crypto, guild))
            elif guild in self.bank: # if no alert has been made, but the guild is in the record.
                self.bank[guild][crypto] = {"daily": 1, "long_term":0, "daily_percent_change": percent, "long_term_percent_change": 0, "long_term_initial_amount":0, "daily_lastalert": 0, "long_term_lastalert":0, "channel": client_message.channel.id, "subscribers": [str(client_message.author.id)], "type": "crypto"}
                self.write_to_file()
                await client_message.add_reaction("\U00002611")
                await asyncio.gather(self.crypto_watcher_daily(crypto, guild))
            else: # no guild or record: make it from scratch
                self.bank[guild] = {}
                self.bank[guild][crypto] = {"daily": 1, "long_term":0, "daily_percent_change": percent, "long_term_percent_change": 0, "long_term_initial_amount":0, "daily_lastalert": 0, "long_term_lastalert":0, "channel": client_message.channel.id, "subscribers": [str(client_message.author.id)], "type": "crypto"}
                self.write_to_file()
                await client_message.add_reaction("\U00002611")
                await asyncio.gather(self.crypto_watcher_daily(crypto, guild))
        except:
            await client_message.channel.send("Something weird with the formatting there. Try again")

    async def set_crypto_alert_long_term(self, args, client, client_message):
        crypto = args[1]
        percent = float(args[2])
        guild = str(client_message.guild.id)
        r = await self.get_crypto_info(args)
        initial_amount = float(r[0]["priceData"][-1]["close"]) # gets the entry position
        try:
            if guild in self.bank and crypto in self.bank[guild] and (self.bank[guild][crypto]["long_term"] == 1): # if a daily alert already exists
                await client_message.channel.send("A long_term alert already exists for " + crypto + " -  remove it first!")
                raise Exception("A long term alert for " + crypto + " already exists!")
            elif guild in self.bank and crypto in self.bank[guild]: # if the crypto is in the system, don't delete it!
                self.bank[guild][crypto]["long_term"] = 1
                self.bank[guild][crypto]["long_term_lastalert"] = 0
                self.bank[guild][crypto]["long_term_percent_change"] = percent
                self.bank[guild][crypto]["long_term_initial_amount"] = initial_amount
                self.bank[guild][crypto]["channel"] = client_message.channel.id # yes - this will overwrite whatever the other setting makes (daily will overwrite long, and so forth). can fix later.
                if str(client_message.author.id) not in self.bank[guild][crypto]["subscribers"]: # don't destroy the subscriber list. yes, we should probably make a separate list for short vs long term later.
                    self.bank[guild][crypto]["subscribers"].append(str(client_message.author.id)) # if already subscribed, do nothing.
                self.write_to_file()
                await client_message.add_reaction("\U00002611")
                await asyncio.gather(self.crypto_watcher_long_term(crypto, guild))
            elif guild in self.bank: # if no alert has been made, but the guild is in the record.
                self.bank[guild][crypto] = {"daily": 0, "long_term":1, "daily_percent_change": 0, "long_term_percent_change": percent, "long_term_initial_amount":initial_amount, "daily_lastalert": 0, "long_term_lastalert":0, "channel": client_message.channel.id, "subscribers": [str(client_message.author.id)], "type": "crypto"}
                self.write_to_file()
                await client_message.add_reaction("\U00002611")
                await asyncio.gather(self.crypto_watcher_long_term(crypto, guild))
            else: # no guild or record: make it from scratch
                self.bank[guild] = {}
                self.bank[guild][crypto] = {"daily": 0, "long_term":1, "daily_percent_change": 0, "long_term_percent_change": percent, "long_term_initial_amount":initial_amount, "daily_lastalert": 0, "long_term_lastalert":0, "channel": client_message.channel.id, "subscribers": [str(client_message.author.id)], "type": "crypto"}
                self.write_to_file()
                await client_message.add_reaction("\U00002611")
                await asyncio.gather(self.crypto_watcher_long_term(crypto, guild))
        except:
            await client_message.channel.send("Something weird with the formatting there. Try again")


    async def remove_stock_alert_daily(self, args, client, client_message):
        stock = args[1]
        guild = str(client_message.guild.id)
        if guild in self.bank and stock in self.bank[guild] and self.bank[guild][stock]["type"] == "stock" and (self.bank[guild][stock]["daily"] == 1): # if a daily alert already exists
            self.bank[guild][stock]["daily"] = 0
            self.bank[guild][stock]["daily_lastalert"] = 0
            if self.bank[guild][stock]["long_term"] == 0:
                del self.bank[guild][stock] # this should delete the record if no active alerts remain
            self.current_watchers -= 1
            self.write_to_file()
            await client_message.add_reaction("\U00002611")
        else:
            await client_message.channel.send("Didn't find a daily stock alert for " + stock + ". Check alerts with showalerts")
            
    async def remove_crypto_alert_daily(self, args, client, client_message):
        crypto = args[1]
        guild = str(client_message.guild.id)
        if guild in self.bank and crypto in self.bank[guild] and self.bank[guild][crypto]["type"] == "crypto" and self.bank[guild][crypto]["daily"] == 1: # if a daily alert already exists
            self.bank[guild][crypto]["daily"] = 0
            self.bank[guild][crypto]["daily_lastalert"] = 0
            if self.bank[guild][crypto]["long_term"] == 0:
                del self.bank[guild][crypto] # this should delete the record if no active alerts remain
            self.current_watchers -= 1
            self.write_to_file()
            await client_message.add_reaction("\U00002611")
        else:
            await client_message.channel.send("No daily crypto alert for " + crypto + ". Check alerts with showalerts")

    async def remove_stock_alert_long_term(self, args, client, client_message):
        stock = args[1]
        guild = str(client_message.guild.id)
        if guild in self.bank and stock in self.bank[guild] and self.bank[guild][stock]["type"] == "stock" and self.bank[guild][stock]["long_term"] == 1:# if a daily alert already exists
            self.bank[guild][stock]["long_term"] = 0
            self.bank[guild][stock]["long_term_lastalert"] = 0
            if self.bank[guild][stock]["daily"] == 0:
                del self.bank[guild][stock] # this should delete the record if no active alerts remain
            self.current_watchers -= 1
            self.write_to_file()
            await client_message.add_reaction("\U00002611")
        else:
            await client_message.channel.send("No long term stock alert for " + stock + ". Check alerts with showalerts")

    async def remove_crypto_alert_long_term(self, args, client, client_message):
        crypto = args[1]
        guild = str(client_message.guild.id)
        if guild in self.bank and crypto in self.bank[guild] and self.bank[guild][crypto]["type"] == "crypto" and (self.bank[guild][crypto]["long_term"] == 1): # if a daily alert already exists
            self.bank[guild][crypto]["long_term"] = 0
            self.bank[guild][crypto]["long_term_lastalert"] = 0
            if self.bank[guild][crypto]["daily"] == 0:
                del self.bank[guild][crypto] # this should delete the record if no active alerts remain
            self.current_watchers -= 1
            self.write_to_file()
            await client_message.add_reaction("\U00002611")
        else:
            await client_message.channel.send("No long term crypto alert for " + crypto + ". Check alerts with showalerts")

    async def show_alerts(self, args, client, client_message):
        output = ""
        guild = str(client_message.guild.id)
        odd_even_counter = 0
        if guild in self.bank:
            for alerts in self.bank[guild]:
                amount_to_round = 2
                initial = self.bank[guild][alerts]["long_term_initial_amount"]
                if initial < 0.01:
                    amount_to_round = 8
                if odd_even_counter % 2 == 0: # make it orange
                    if self.bank[guild][alerts]["long_term"] == 1: #self.bank[guild][stock]["long_term_initial_amount"] + " +/- " + self.bank[guild][stock]["long_term_percent_change"] + "%"
                        output += self.odd_or_even_coloring(odd_even_counter,"(" + self.bank[guild][alerts]["type"] + ") " + alerts + " - INITIAL AMT: " + format(initial, "." + str(amount_to_round) + "f") + " - NOTIFY THRESHOLD: " + format(self.bank[guild][alerts]["long_term_percent_change"] * 100, ".2f") + "%" + " [Long Term]")
                        odd_even_counter += 1
                    if self.bank[guild][alerts]["daily"] == 1:
                        output += self.odd_or_even_coloring(odd_even_counter, "(" + self.bank[guild][alerts]["type"] + ") " + alerts + " - NOTIFY THRESHOLD: " + format(self.bank[guild][alerts]["daily_percent_change"] * 100, ".2f") + "%" + " [Daily]")
                        odd_even_counter += 1
                else: # make it blue
                    if self.bank[guild][alerts]["long_term"] == 1: #self.bank[guild][stock]["long_term_initial_amount"] + " +/- " + self.bank[guild][stock]["long_term_percent_change"] + "%"
                        output += self.odd_or_even_coloring(odd_even_counter, "(" + self.bank[guild][alerts]["type"] + ") " + alerts + " - INITIAL AMT: " + format(initial, "." + str(amount_to_round) + "f") + " - NOTIFY THRESHOLD: " + format(self.bank[guild][alerts]["long_term_percent_change"] * 100, ".2f") + "%" + "  [Long Term]")
                        odd_even_counter += 1
                    if self.bank[guild][alerts]["daily"] == 1:
                        output += self.odd_or_even_coloring(odd_even_counter, "(" + self.bank[guild][alerts]["type"] + ") " + alerts + " - NOTIFY THRESHOLD: " + format(self.bank[guild][alerts]["daily_percent_change"] * 100, ".2f") + "%" + " [Daily]")
                        odd_even_counter += 1
                
                
        if output == "":
            output = "No alerts are set up yet!"
        else:
            output += ""
        await client_message.channel.send(output)

    async def subscribe_to_alert(self, args, client, client_message):
        stock = args[1]
        guild = str(client_message.guild.id)
        if guild in self.bank and stock in self.bank[guild]: # if the alert exists
            if not str(client_message.author.id)  in self.bank[guild][stock]["subscribers"]: # if not already subscribed
                self.bank[guild][stock]["subscribers"].append(str(client_message.author.id))
                await client_message.add_reaction("\U00002611")
                self.write_to_file()
            else:
                await client_message.channel.send("Looks like you're already subscribed to " + stock + "!")
        else:
            await client_message.channel.send("No alerts for " + stock + " yet. Make one first!")

    async def unsubscribe_to_alert(self, args, client, client_message):
        stock = args[1]
        guild = str(client_message.guild.id)
        if guild in self.bank and stock in self.bank[guild]: # if the alert exists
            if str(client_message.author.id)  in self.bank[guild][stock]["subscribers"]: # if already subscribed
                self.bank[guild][stock]["subscribers"].remove(str(client_message.author.id)) # remove the person from the list
                await client_message.add_reaction("\U00002611")
                self.write_to_file()
            else:
                await client_message.channel.send("Looks like you're already unsubscribed to " + stock + "!")
        else:
            await client_message.channel.send("No alerts for " + stock + " yet. Make one first!")

    async def list_subscribers(self, args, client, client_message):
        guild = str(client_message.guild.id)
        if len(args) < 2:
            await client_message.channel.send("Specify a stock to check!" )
        else:
            stock = args[1]
            list_of_subs = ""
            if guild in self.bank and stock in self.bank[guild]:# if the stock is in the bank
                for subs in self.bank[guild][stock]["subscribers"]:
                    list_of_subs += client.get_user(int(subs)).name + "\n"
                await client_message.channel.send("```Subscribers for stock: " + stock + "\n" + list_of_subs + "```" )
            else:
                await client_message.channel.send("```No subscribers for stock: " + stock + "```")

    # https://www.writebots.com/discord-text-formatting/
    def odd_or_even_coloring(self, number, message):
        if number % 2 == 0: #even
            return "```fix\n" + message + "\n```"
        else:
            return "```bash\n" + "\"" + message + "\"\n```"