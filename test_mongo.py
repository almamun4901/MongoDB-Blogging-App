from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["blogdb"]

print("Connected to MongoDB:", db.list_collection_names())
