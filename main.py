import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

from DataBase.MongoDB import getChatBotsCollection
from server.fastApi.modules.awsKeysManagement import getAwsSecretKey
from server.fastApi.modules.databaseManagement import getContentMappingList
from src.DataBaseConstants import CHATBOT_ID, CONTENT_LIST, USER_ID
from src.training.train_model import getDocumentsList

import datetime

if __name__ == "__main__":
    uid = "G2pJbmdftsc0uj5ZH2IguWggh4z1"
    botID = "e0de187e-10d5-4f02-a0c8-dd25b922d557"
    # print(getChatBotsCollection().find_one({USER_ID: uid, CHATBOT_ID: botID})[CONTENT_LIST] or [])
    print(getAwsSecretKey("FIREBASE_CONFIG"))
