from fastapi import HTTPException
from DataBase.MongoDB import getContentStoreCollection, getUsersCollection,getChatBotsCollection
from src.DataBaseConstants import EMAIL_ID, USER_ID,CHATBOT_ID,CHATBOT_LIST,CONTENT_ID,CONTENT,CHATBOT_NAME,CHATBOT_STATUS
from src.logger.logger import GlobalLogger
from typing import List, Dict
import uuid
def createUserIfNotExist(uid:str,email:str):
    if not getUsersCollection().find_one({USER_ID:uid}):
        getUsersCollection().insert_one({USER_ID:uid,EMAIL_ID:email})
        GlobalLogger.debug("User created successfully UID: "+uid)
        
def createChatBot(uid:str):
    user = getUsersCollection().find_one({USER_ID: uid})
    if user is None:
        HTTPException(status_code=404, detail="Something Went wrong")
    botID=uuid.uuid4()
    bot_id_list = user.get(CHATBOT_LIST, [])
    bot_id_list.append({CHATBOT_ID:botID,CHATBOT_NAME:"Untitled Bot",CHATBOT_STATUS:'untrained'})
    getUsersCollection().update_one({"USER_ID": uid}, {"$set": {CHATBOT_LIST: bot_id_list}})
    getChatBotsCollection().insert_one({USER_ID:uid,CHATBOT_ID:botID})
    GlobalLogger.debug("Chatbot creating initialted UID: "+botID)
    return botID

def myChatBotsList(uid:str):
    user = getUsersCollection().find_one({USER_ID: uid})
    if user is None:
        return []
    return user.get(CHATBOT_LIST, [])
    
def getContentList(uid: str, botID: str):
    """
    Returns the content list corresponding to a bot.

    Parameters:
        uid (str): Current User ID.
        botID (str): Bot ID from which content will be retrieved.

    Returns:
        list or None: List of dictionaries containing Content ID and Content text, if available.
                     Returns None if no content is found for the given user and bot.
    """ 
    return getChatBotsCollection().find_one({USER_ID: uid, CHATBOT_ID: botID}) or []

        
def storeContent(contentID:str,content:str):
    getContentStoreCollection().insert_one({CONTENT_ID:contentID,CONTENT:content})
    
    
def storeContentList(list:List[Dict[str, str]]):
    getContentStoreCollection().insert_many(list)
    
def insertContentListInBotCollection(botID:str):
    getContentStoreCollection().insert_many(list)
         
    
