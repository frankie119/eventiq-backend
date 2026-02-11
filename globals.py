from pymongo import MongoClient

client = MongoClient("mongodb://127.0.0.1:27017")
db = client.EventsDB
secret_key = '7fb3476643f5ddea0ebc8c517e6402be'