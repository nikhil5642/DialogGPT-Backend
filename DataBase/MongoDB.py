import os

from pymongo import MongoClient

from server.fastApi.modules.awsKeysManagement import get_mongo_uri

MONGO_DB_NAME = "chatbot_data"


class MongoDBCollections:
    USERS_COLLECTION = "chatbot_users"
    CHATBOTS_COLLECTION = "chatbot_list"
    CONTENT_COLLECTION = "content_list"
    CHATBOTS_CONFIG = "chatbot_config"
    CHATBOTS_HISTORY = "chatbot_history"


class MongoManager:
    __instance = None

    @staticmethod
    def getInstance():
        if MongoManager.__instance == None:
            MongoManager()
        return MongoManager.__instance

    def __init__(self):
        if MongoManager.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            uri = get_mongo_uri()
            client = MongoClient(uri)
            MongoManager.__instance = client[MONGO_DB_NAME]


def getCollection():
    return MongoManager.getInstance()


def getUsersCollection():
    return MongoManager.getInstance()[MongoDBCollections.USERS_COLLECTION]


def getChatBotsCollection():
    return MongoManager.getInstance()[MongoDBCollections.CHATBOTS_COLLECTION]


def getContentStoreCollection():
    return MongoManager.getInstance()[MongoDBCollections.CONTENT_COLLECTION]


def getChatBotConfigCollection():
    return MongoManager.getInstance()[MongoDBCollections.CHATBOTS_CONFIG]


def getChatHistoryCollection():
    return MongoManager.getInstance()[MongoDBCollections.CHATBOTS_HISTORY]


if __name__ == "__main__":
    db = MongoManager.getInstance()
    userInfoCollection = db[MongoDBCollections.USER_INFO_COLLECTION]
    print(userInfoCollection.find_one({"userId": 1}))
