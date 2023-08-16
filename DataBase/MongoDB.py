
import os

from pymongo import MongoClient

MONGO_DB_NAME = "chatbot_data"


class MongoDBCollections:
    USERS_COLLECTION = "chatbot_users"
    CHATBOTS_COLLECTION = "chatbot_list"
    CONTENT_COLLECTION = "content_list"


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
            uri = "mongodb+srv://cluster0.hk8u8le.mongodb.net/?authSource=%24external&authMechanism=MONGODB-X509&retryWrites=true&w=majority"
            client = MongoClient(uri,
                                 tls=True,
                                 tlsCertificateKeyFile=os.path.abspath("./DataBase/mongo.pem"))
            MongoManager.__instance = client[MONGO_DB_NAME]


def getCollection():
    return MongoManager.getInstance()


def getUsersCollection():
    return MongoManager.getInstance()[MongoDBCollections.USERS_COLLECTION]

def getChatBotsCollection():
    return MongoManager.getInstance()[MongoDBCollections.CHATBOTS_COLLECTION]

def getContentStoreCollection():
    return MongoManager.getInstance()[MongoDBCollections.CONTENT_COLLECTION]

if __name__ == '__main__':
    db = MongoManager.getInstance()
    userInfoCollection = db[MongoDBCollections.USER_INFO_COLLECTION]
    print(userInfoCollection.find_one({"userId": 1}))
