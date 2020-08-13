'''
Keeps track of a number value for a given discord user, modified through commands.
'''
import os
import json

class Bank:
    def __init__(self, bank_file="bank.log"):
        file_to_open = bank_file
        dir = os.path.dirname(__file__) # absolute dir the script is running in 
        if os.path.getsize(os.path.join(dir, file_to_open)) > 0:
            bank_file = open(os.path.join(dir, file_to_open), "w+")
            bank = json.loads(bank_file.read()) # Json to Dictionary
        else:
            bank = {} # if there's no file already, make a new bank.

    def increment(self, userid, amt):
        if not isinstance(amt, int):
            raise Exception("Incorrect type for amt") 
        elif not isinstance(userid, int):
            raise Exception("Incorrect type for userid") 
        if userid in bank:
            bank[userid] += amt
        else:
            bank[userid] = amt
        bank_file.write(json.dumps(bank)) # not very efficient
    
    def decrement(self, userid, amt):
        if not isinstance(amt, int):
            raise Exception("Incorrect type for amt") 
        elif not isinstance(userid, int):
            raise Exception("Incorrect type for userid") 
        if userid in bank:
            bank[userid] -= amt
        else:
            bank[userid] = -amt
        bank_file.write(json.dumps(bank)) # not very efficient

    def set_to(self, userid, amt):
        if not isinstance(amt, int):
            raise Exception("Incorrect type for amt") 
        elif not isinstance(userid, int):
            raise Exception("Incorrect type for userid") 
            bank[userid] = amt

        bank_file.write(json.dumps(bank)) # not very efficient