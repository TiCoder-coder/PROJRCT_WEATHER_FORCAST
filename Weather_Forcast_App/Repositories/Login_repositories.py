from pymongo import MongoClient, ASCENDING
from decouple import config
from bson import ObjectId

client = MongoClient(config("MONGO_URI"))
db = client[config("DB_NAME")]

login_collection = db["logins"]

login_collection.create_index([("userName", ASCENDING)], unique=True)
login_collection.create_index([("email", ASCENDING)], unique=True)

class LoginRepository:
    @staticmethod
    def insert_one(data: dict):
        return login_collection.insert_one(data)

    @staticmethod
    def find_all():
        return list(login_collection.find())

    @staticmethod
    def find_by_id(user_id):
        return login_collection.find_one({"_id": ObjectId(str(user_id))})

    @staticmethod
    def find_by_username(userName: str):
        return login_collection.find_one({"userName": userName})

    @staticmethod
    def find_by_username_or_email(identifier: str):
        return login_collection.find_one({"$or": [{"userName": identifier}, {"email": identifier}]})

    @staticmethod
    def update_by_id(user_id, update_data: dict):
        return login_collection.update_one({"_id": ObjectId(str(user_id))}, {"$set": update_data})

    @staticmethod
    def delete_by_id(user_id):
        return login_collection.delete_one({"_id": ObjectId(str(user_id))})
