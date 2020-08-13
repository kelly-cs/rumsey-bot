'''
Keeps track of a number value for a given discord user, modified through commands.
'''
import os
import json
import discord 
import operator

class Bank:
    def __init__(self, bank_file="bank.log"):
        self.bank = {}
        self.file_to_open = bank_file
        self.dir = os.path.dirname(__file__) # absolute dir the script is running in 
        self.initial_bank_load()
        self.money_sign = "$"

    def initial_bank_load(self):
        if os.path.getsize(os.path.join(self.dir, self.file_to_open)) > 0: # if there's data in there
            bank_file = open(os.path.join(self.dir, self.file_to_open), "r")
            self.bank = json.loads(bank_file.read()) # Json to Dictionary
            bank_file.flush()
            bank_file.close()
            print(self.bank)
        else:
            self.bank = {}
        

    def write_to_file(self):
        bank_file = open(os.path.join(self.dir, self.file_to_open), "w")
        bank_file.write(json.dumps(self.bank)) # not very efficient
        bank_file.flush()
        os.fsync(bank_file.fileno())
        bank_file.close()

    def increment(self, userid, amt):
        if not isinstance(amt, int):
            raise Exception("Incorrect type for amt") 

        if userid in self.bank:
            self.bank[userid] += amt
        else:
            self.bank[userid] = amt
        self.write_to_file()
    
    def decrement(self, userid, amt):
        if not isinstance(amt, int):
            raise Exception("Incorrect type for amt") 
        if userid in self.bank:
            self.bank[userid] -= amt
        else:
            self.bank[userid] = -amt
        self.write_to_file()

    def set_to(self, userid, amt):
        if not isinstance(amt, int):
            raise Exception("Incorrect type for amt") 
        self.bank[userid] = amt
        self.write_to_file()

    def get_balance(self, userid):
        if userid in self.bank:
            return self.bank[userid]
    
    def remove_id(self, userid):
        if userid in self.bank:
            self.bank.pop(userid)



    def all_balances(self, client):
        
        output = ""
        # https://careerkarma.com/blog/python-sort-a-dictionary-by-value/#:~:text=To%20sort%20a%20dictionary%20by%20value%20in%20Python%20you%20can,Dictionaries%20are%20unordered%20data%20structures.
        balances = sorted(self.bank.items(), key=lambda x: x[1], reverse=True)

        for sorted_users in balances:
            username = client.get_user(int(sorted_users[0])).name
            if balances.index(sorted_users) == 0:
                output += ("```diff\n- " + username + "\t" + self.money_sign + str(sorted_users[1]) + "\n```") # makes it red (the -)
            elif balances.index(sorted_users) == 1:
                output += ("```fix\n " + username + "\t" + self.money_sign + str(sorted_users[1]) + "\n```") # makes it yellow
            elif balances.index(sorted_users) == 2:
                output += ("```fix\n " + username + "\t" + self.money_sign + str(sorted_users[1]) + "\n```") # makes it yellow
            else:
                output += ("```diff\n+ " + username + "\t" + self.money_sign + str(sorted_users[1]) + "\n```") # makes it green
        return output
