from fastapi import HTTPException
from DataBase.MongoDB import getContentStoreCollection, getUsersCollection,getChatBotsCollection
from src.DataBaseConstants import CONTENT_LIST, EMAIL_ID, LAST_UPDATED, USER_ID,CHATBOT_ID,CHATBOT_LIST,CONTENT_ID,CONTENT,CHATBOT_NAME,CHATBOT_STATUS,CREATED_ON,CHAR_COUNT
from src.data_sources.utils import generateContentItem
from src.logger.logger import GlobalLogger
from typing import List, Dict
import uuid
from datetime import datetime

def createUserIfNotExist(uid:str,email:str):
    if not getUsersCollection().find_one({USER_ID:uid}):
        getUsersCollection().insert_one({USER_ID:uid,EMAIL_ID:email})
        GlobalLogger().debug("User created successfully UID: "+uid)

def getUserInfo(uid):
    return getUsersCollection().find_one({USER_ID:uid},{"_id": 0, CHATBOT_LIST:0}) or {}

def createChatBot(uid:str,chatbotname):
    user = getUsersCollection().find_one({USER_ID: uid})
    if user is None:
        HTTPException(status_code=404, detail="Something Went wrong")
    botID=str(uuid.uuid4())
    bot_id_list = user.get(CHATBOT_LIST, [])
    bot_id_list.append({CHATBOT_ID:botID,CHATBOT_NAME:chatbotname,CHATBOT_STATUS:'untrained',LAST_UPDATED:datetime.now(),CREATED_ON:datetime.now()})
    getUsersCollection().update_one({USER_ID: uid}, {"$set": {CHATBOT_LIST: bot_id_list}})
    getChatBotsCollection().insert_one({USER_ID:uid,CHATBOT_ID:botID,CHATBOT_NAME:chatbotname,CHATBOT_STATUS:'untrained',LAST_UPDATED:datetime.now(),CREATED_ON:datetime.now()})
    GlobalLogger().debug("Chatbot creating initialted UID: "+botID)
    return botID

def updateChatBotStatus(uid,botID,status):
    user = getUsersCollection().find_one({USER_ID: uid})
    if user is None:
        HTTPException(status_code=404, detail="Something Went wrong")
    botID=str(uuid.uuid4())
    bot_id_list = user.get(CHATBOT_LIST, [])
    for bot in bot_id_list:
        if(bot[CHATBOT_ID]==botID):
            bot[CHATBOT_STATUS]=status
            bot[LAST_UPDATED]=datetime.now()
    getUsersCollection().update_one({USER_ID: uid}, {"$set": {CHATBOT_LIST: bot_id_list}})
    
def updateChatbotName(uid,botID,newName):
    user = getUsersCollection().find_one({USER_ID: uid})
    if user is None:
        HTTPException(status_code=404, detail="Something Went wrong")
    bot_id_list = user.get(CHATBOT_LIST, [])
    for bot in bot_id_list:
        if(bot[CHATBOT_ID]==botID):
            bot[CHATBOT_NAME]=newName
            bot[LAST_UPDATED]=datetime.now()
    getUsersCollection().update_one({USER_ID: uid}, {"$set": {CHATBOT_LIST: bot_id_list}})
    getChatBotsCollection().update_one({USER_ID:uid,CHATBOT_ID:botID}, {"$set": {CHATBOT_NAME: newName}})
   
   

def myChatBotsList(uid:str):
    user = getUsersCollection().find_one({USER_ID: uid})
    if user is None:
        return []
    return user.get(CHATBOT_LIST, [])
    
def getContentMappingList(uid: str, botID: str):
    """
    Returns the content list corresponding to a bot.

    Parameters:
        uid (str): Current User ID.
        botID (str): Bot ID from which content will be retrieved.

    Returns:
        list or None: List of dictionaries containing Content ID and Content text, if available.
                     Returns None if no content is found for the given user and bot.
    """ 
    try:
        return getChatBotsCollection().find_one({USER_ID: uid, CHATBOT_ID: botID})[CONTENT_LIST] or []
    except:
        return []

                
def getChatBotInfo(uid:str,botID:str):
    return getChatBotsCollection().find_one({USER_ID: uid, CHATBOT_ID: botID}, {"_id": 0, USER_ID: 0,CHATBOT_ID:0,CONTENT_LIST:0}) or {}
         
     
def storeContent(contentID:str,content:str):
    getContentStoreCollection().insert_one(generateContentItem(contentID,content))

def updateContent(uid:str,botID:str,contentID:str,content:str):
    contentList=getContentMappingList(uid,botID)
    for contentItem in contentList:
        if contentItem[CONTENT_ID]==contentID:
            contentItem[LAST_UPDATED]=datetime.now()
            contentItem[CHAR_COUNT]=len(content)
    insertContentListInBotCollection(uid,botID,contentList)        
    getContentStoreCollection().update_one({CONTENT_ID:contentID},{"$set":{CONTENT:content,LAST_UPDATED:datetime.now()}})

def getContent(contentID:str):
    return getContentStoreCollection().find_one({CONTENT_ID:contentID})[CONTENT]
  
    
def storeContentList(list):
    if(list!=[]):
        getContentStoreCollection().insert_many(list)
    
def insertContentListInBotCollection(uid:str,botID:str,newContentList):
    getChatBotsCollection().update_one({USER_ID: uid, CHATBOT_ID: botID}, {"$set": {CONTENT_LIST: newContentList}})

