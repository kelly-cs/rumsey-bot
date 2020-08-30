'''
Util - Update Mongo DB

This script will convert old-version .log files to your cloud/Atlas mongodb schema. 
RUN THIS ONLY ONCE AND CONFIRM YOUR DATA HAS BEEN SUBMITTED BEFORE TRYING AGAIN - just to ensure you don't duplicate data unnecessarily, or cause weird stuff to happen.

'''

# https://stackoverflow.com/questions/49510049/how-to-import-json-file-to-mongodb-using-python/49510257

import json
from pymongo import MongoClient

mongodb_client = MongoClient("connection string here")
db = mongodb_client['rumsey']
collection = db['rumsey']

with open('bank.log') as f:
    file_data = json.load(f)

# if pymongo < 3.0, use insert()
# collection.insert(file_data)
# if pymongo >= 3.0 use insert_one() for inserting one document
#collection.insert_one(file_data)
# if pymongo >= 3.0 use insert_many() for inserting many documents
#print(type(file_data))
#collection.insert_many(file_data)
collection.update_one({"_id":"guild"}, {"$set": file_data}, upsert=True)
mongodb_client.close()