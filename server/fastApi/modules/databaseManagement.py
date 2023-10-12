from fastapi import HTTPException
from DataBase.MongoDB import getChatBotConfigCollection, getChatHistoryCollection, getContentStoreCollection, getUsersCollection,getChatBotsCollection
from src.BaseConstants import BASE_CHAT_BUBBLE_COLOR, BASE_CHAT_INITIAL_MESSAGE, BASE_CHATGPT_PROMPT, BASE_USER_MSG_COLOR
from src.DataBaseConstants import BASE_PROMPT, CHAT_ID, COMPLETE, CONTENT_LIST, EMAIL_ID, FREE_PLAN, GPT_3_5_TURBO, HISTORY, INTERFACE, LAST_UPDATED, LIGHT, MESSAGE_CREDITS, MESSAGE_LIMIT,MESSAGE_USED, MODEL, MODEL_VERSION, PROMPT, SUBSCRIPTION_CANCELED, SUBSCRIPTION_PLAN, SUBSCRIPTION_STATUS, TEMPERATURE, TRAINED, USER_ID,CHATBOT_ID,CHATBOT_LIST,CONTENT_ID,CONTENT,CHATBOT_NAME,CHATBOT_STATUS,CREATED_ON,CHAR_COUNT,SUBSCRIPTION_ID,INITIAL_MESSAGE,QUICK_PROMPTS,THEME,PROFILE_PICTURE,USER_MSG_COLOR,DISPLAY_NAME,CHAT_ICON,CHAT_BUBBLE_COLOR
from src.data_sources.utils import generateContentItem
from src.emailSender.sendEmail import sendWelcomeEmail
from src.logger.logger import GlobalLogger
from typing import List, Dict
import uuid
from datetime import datetime
from src.scripts.chatbotUtils import getChatBotLimitAsPerPlan


def createUserIfNotExist(uid:str,email:str):
    if not getUsersCollection().find_one({USER_ID:uid}):
        getUsersCollection().insert_one({USER_ID:uid,EMAIL_ID:email,MESSAGE_USED:0,
            MESSAGE_LIMIT:30,SUBSCRIPTION_PLAN:FREE_PLAN,SUBSCRIPTION_STATUS:COMPLETE})
        GlobalLogger().debug("User created successfully UID: "+uid)
        sendWelcomeEmail(email)

def getUserInfo(uid):
    return getUsersCollection().find_one({USER_ID:uid},{"_id": 0, CHATBOT_LIST:0}) or {}

def getRemainingMessageCredits(uid):
    userDoc= getUserInfo(uid)
    return getMessageCredits(userDoc)
def getMessageCredits(userDoc):
    if userDoc!={}:
        return {SUBSCRIPTION_PLAN:userDoc.get(SUBSCRIPTION_PLAN,FREE_PLAN),MESSAGE_CREDITS:max(0,userDoc.get(MESSAGE_LIMIT,0)-userDoc.get(MESSAGE_USED,0))}
    else:
        return {SUBSCRIPTION_PLAN:FREE_PLAN,MESSAGE_CREDITS:0}

def updateMessageUsed(uid:str,msgUsed:int): 
    getUsersCollection().update_one({USER_ID: uid}, {"$set": {MESSAGE_USED: msgUsed}})
    
def createChatBot(uid:str,chatbotname):
    user = getUsersCollection().find_one({USER_ID: uid})
    if user is None:
        raise HTTPException(status_code=501, detail="Something Went wrong")
    botID=str(uuid.uuid4())
    bot_id_list = user.get(CHATBOT_LIST, [])
    max_allowed_bots= getChatBotLimitAsPerPlan(user.get(SUBSCRIPTION_PLAN, FREE_PLAN))
    if(len(bot_id_list)>=max_allowed_bots):
        raise HTTPException(status_code=501, detail="You have reached the maximum limit of chatbots for your plan")
    bot_id_list.append({CHATBOT_ID:botID,CHATBOT_NAME:chatbotname,CHATBOT_STATUS:'untrained',LAST_UPDATED:datetime.now(),CREATED_ON:datetime.now()})
    getUsersCollection().update_one({USER_ID: uid}, {"$set": {CHATBOT_LIST: bot_id_list}})
    getChatBotsCollection().insert_one({USER_ID:uid,CHATBOT_ID:botID,CHATBOT_NAME:chatbotname,CHATBOT_STATUS:'untrained',LAST_UPDATED:datetime.now(),CREATED_ON:datetime.now()})
    GlobalLogger().debug("Chatbot creating initialted UID: "+botID)
    return botID

def updateChatBotStatus(uid,botID,status):
    if status==TRAINED:
        getChatBotsCollection().update_one({USER_ID: uid, CHATBOT_ID: botID}, {"$set": {CHATBOT_STATUS: status,LAST_UPDATED:datetime.now()}})
    else:
        getChatBotsCollection().update_one({USER_ID: uid, CHATBOT_ID: botID}, {"$set": {CHATBOT_STATUS: status}})
    
    user = getUsersCollection().find_one({USER_ID: uid})
    if user is None:
        HTTPException(status_code=404, detail="Something Went wrong")
    botID=str(uuid.uuid4())
    bot_id_list = user.get(CHATBOT_LIST, [])
    for bot in bot_id_list:
        if(bot[CHATBOT_ID]==botID):
            bot[CHATBOT_STATUS]=status
            if(status==TRAINED):
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
   
   
def getUserChatBotInfo(uid:str):
    user = getUsersCollection().find_one({USER_ID: uid})
    if user is None:
        return []
    return user.get(CHATBOT_LIST, []),getChatBotLimitAsPerPlan(user.get(SUBSCRIPTION_PLAN, FREE_PLAN))
    
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

def getChatInterface(botID:str):
    document = getChatBotConfigCollection().find_one({CHATBOT_ID: botID})
    if document:
        interface_data = document.get(INTERFACE, {})
    else:
        interface_data = {}
        
    if interface_data == {}:
        return {INITIAL_MESSAGE:BASE_CHAT_INITIAL_MESSAGE,QUICK_PROMPTS:"",THEME:LIGHT,PROFILE_PICTURE:None,USER_MSG_COLOR:BASE_USER_MSG_COLOR,DISPLAY_NAME:"",CHAT_ICON:None,CHAT_BUBBLE_COLOR:BASE_CHAT_BUBBLE_COLOR}
    else:
        return {INITIAL_MESSAGE:interface_data[INITIAL_MESSAGE] or BASE_CHAT_INITIAL_MESSAGE,QUICK_PROMPTS:interface_data[QUICK_PROMPTS],THEME:interface_data[THEME],PROFILE_PICTURE:interface_data[PROFILE_PICTURE],USER_MSG_COLOR:interface_data[USER_MSG_COLOR],DISPLAY_NAME:interface_data[DISPLAY_NAME],CHAT_ICON:interface_data[CHAT_ICON],CHAT_BUBBLE_COLOR:interface_data[CHAT_BUBBLE_COLOR]}    
        

def updateChatInterface(uid:str,botID:str,initialMessage:str,quickPrompts:str,theme:str,profilePicture:str,userMsgColor:str,displayName:str,chatIcon:str,chatBubbleColor:str):
    interface_data={ INITIAL_MESSAGE:initialMessage,QUICK_PROMPTS:quickPrompts,THEME:theme,PROFILE_PICTURE:profilePicture,USER_MSG_COLOR:userMsgColor,DISPLAY_NAME:displayName,CHAT_ICON:chatIcon,CHAT_BUBBLE_COLOR:chatBubbleColor}
    
    if not getChatBotConfigCollection().find_one({USER_ID:uid,CHATBOT_ID:botID}):
         getChatBotConfigCollection().insert_one({USER_ID:uid,CHATBOT_ID:botID,INTERFACE:interface_data})
    else:
        getChatBotConfigCollection().update_one({USER_ID: uid, CHATBOT_ID: botID}, {"$set": {INTERFACE: interface_data}})

def getChatModel(botID:str):
    document = getChatBotConfigCollection().find_one({CHATBOT_ID: botID})
    if document:
        model_data = document.get(MODEL, {})
    else:
        model_data = {}
    if model_data == {}:
        return {PROMPT:BASE_CHATGPT_PROMPT,BASE_PROMPT:BASE_CHATGPT_PROMPT,MODEL_VERSION:GPT_3_5_TURBO,TEMPERATURE:0}    
    else :
        return {PROMPT:model_data[PROMPT] or BASE_CHATGPT_PROMPT,BASE_PROMPT:BASE_CHATGPT_PROMPT,MODEL_VERSION:model_data[MODEL_VERSION],TEMPERATURE:model_data[TEMPERATURE]}    


def updateChatModel(uid:str,botID:str,prompt:str,modelVersion:str,temperature:float):
    model_data={ PROMPT:prompt,MODEL_VERSION:modelVersion,TEMPERATURE:temperature}
    
    if not getChatBotConfigCollection().find_one({USER_ID:uid,CHATBOT_ID:botID}):
         getChatBotConfigCollection().insert_one({USER_ID:uid,CHATBOT_ID:botID,MODEL:model_data})
    else:
        getChatBotConfigCollection().update_one({USER_ID: uid, CHATBOT_ID: botID}, {"$set": {MODEL: model_data}})

def deleteChatbot(uid,botID):
    user = getUsersCollection().find_one({USER_ID: uid})
    if user is None:
        HTTPException(status_code=404, detail="Something Went wrong")
    bot_id_list = user.get(CHATBOT_LIST, [])
    for bot in bot_id_list:
        if(bot[CHATBOT_ID]==botID):
            bot_id_list.remove(bot)
    getUsersCollection().update_one({USER_ID: uid}, {"$set": {CHATBOT_LIST: bot_id_list}})
    contentIDList=[item[CONTENT_ID] for item in getContentMappingList(uid,botID)]
    deleteContentID(contentIDList)
    getChatBotsCollection().delete_one({USER_ID:uid,CHATBOT_ID:botID})
   
def deleteContentID(contentIdList):
    getContentStoreCollection().delete_many({CONTENT_ID: {'$in': contentIdList}})

def storeChatHistory(botId,chatId,history):
    history = [message.dict() for message in history]
    existing_history = getChatHistoryCollection().find_one({CHAT_ID: chatId})
    if existing_history:
        getChatHistoryCollection().update_one(
            {CHAT_ID: chatId},
            {"$set": {HISTORY: history,LAST_UPDATED:datetime.now()}}
        )
    else:
        getChatHistoryCollection().insert_one({
            CHAT_ID: chatId,
            CHATBOT_ID: botId,
            HISTORY: history,
            LAST_UPDATED:datetime.now()
        })
def getChatHistory(chatbotId):
    # Assuming you have a function getChatHistoryCollection that returns the MongoDB collection
    cursor = getChatHistoryCollection().find({CHATBOT_ID: chatbotId}, {"_id": 0})

    # Convert the cursor to a list
    history_list = list(cursor)

    if history_list:
        return history_list
    else:
        return []


def get_subscription_plan(user_id: str) -> str:
    user_document = getUsersCollection().find_one({USER_ID: user_id})
    if user_document and SUBSCRIPTION_PLAN in user_document:
        return user_document[SUBSCRIPTION_PLAN]
    else:
        return FREE_PLAN
def get_subscription_id(user_id: str) -> str:
    user_document = getUsersCollection().find_one({USER_ID: user_id})
    if user_document and SUBSCRIPTION_ID in user_document:
        return user_document[SUBSCRIPTION_ID]
    else:
        return None

def handle_subscription_creation(user_id,subscription_status,subscription_plan,subscription_id,message_limit):
    getUsersCollection().update_one(
        {USER_ID: user_id},
        {'$set': {
            SUBSCRIPTION_STATUS: subscription_status,
            SUBSCRIPTION_PLAN: subscription_plan,
            SUBSCRIPTION_ID:subscription_id,
            MESSAGE_LIMIT:message_limit
        }}
    )

def handle_subscription_update(user_id,subscription_status,subscription_plan,message_limit):
        
    if(subscription_status==SUBSCRIPTION_CANCELED):
        getUsersCollection().update_one(
        {USER_ID: user_id},
        {'$set': {
            SUBSCRIPTION_STATUS: subscription_status,
            SUBSCRIPTION_PLAN: subscription_plan,
            MESSAGE_LIMIT:0,
            MESSAGE_USED:0
        }}
        )
    else:
        getUsersCollection().update_one(
        {USER_ID: user_id},
        {'$set': {
            SUBSCRIPTION_STATUS: subscription_status,
            SUBSCRIPTION_PLAN: subscription_plan,
            MESSAGE_LIMIT:message_limit,
        }}
    )
    

def handle_subscription_deletion(subscriptio_id):
    getUsersCollection().update_one(
        {SUBSCRIPTION_ID: subscriptio_id},
        { '$set': {
            SUBSCRIPTION_STATUS: "",
            SUBSCRIPTION_PLAN: FREE_PLAN,
            SUBSCRIPTION_ID:None,
            MESSAGE_LIMIT:0,
            MESSAGE_USED:0
            },
         } 
    )



def to_camel_case(s):
    parts = s.split('_')
    return parts[0] + ''.join(p.capitalize() for p in parts[1:])