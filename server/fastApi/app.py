from typing import List
from fastapi import Depends, FastAPI, HTTPException, BackgroundTasks
from DataBase.MongoDB import getChatBotsCollection, getUsersCollection
from server.fastApi.modules.databaseManagement import createChatBot, createUserIfNotExist, getChatBotInfo, getContent, getContentMappingList, getUserInfo, myChatBotsList, updateChatBotStatus, updateChatbotName
from server.fastApi.modules.firebase_verification import  generate_JWT_Token, get_current_user, verifyFirebaseLogin
from src.DataBaseConstants import CHATBOT_ID, CHATBOT_STATUS, CONTENT_LIST, LAST_UPDATED, RESULT, SOURCE, SOURCE_TYPE, STATUS, SUCCESS,CHATBOT_LIST, TRAINED, URL,NEWLY_ADDED, USER_ID,TRAINING,QUERY,REPLY,ERROR,UNTRAINED
from starlette.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from src.data_sources.text_loader import saveText
from datetime import datetime
from src.data_sources.urls_loader import get_all_urls_mapping, get_filtered_content_mapping, get_final_content_mapping, get_url_list_mapping
from src.training.consume_model import replyToQuery
from src.training.train_model import trainChatBot

app = FastAPI()


origins = ["http://localhost:3000",
           "https://www.chessmeito.com",
           "https://chessmeito.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory="assets"), name="assets")


@app.get("/")
async def root():
    return {"message": "Hello Bigger Applications!"}

class AuthenticationModel(BaseModel):
    token:str

class BaseChatBotModel(BaseModel):
    botID:str
class URLModel(BaseChatBotModel):
    url: str
    
class TextModel(BaseChatBotModel):
    text: str
    
class ContentModel(BaseModel):
    contentID: str

class ChatBotCreationModel(BaseModel):
    chatBotName:str
    
class ChatBotNameChangeModel(BaseChatBotModel):
    chatBotName:str
class URLListModel(BaseChatBotModel):
    urls: List[str]

class TrainingModel(BaseChatBotModel):
    data:List[dict]

class ReplyModel(BaseChatBotModel):
    query:str
    history:List[List]


@app.post("/authenticate")
def authenticate(data:AuthenticationModel):
    decodedToken=verifyFirebaseLogin(data.token)
    try:
        uid = decodedToken.get('uid')
        email=decodedToken.get('email')
        createUserIfNotExist(uid,email)
        jwt_token=generate_JWT_Token(uid)
        return {SUCCESS:True,"access_token": jwt_token, "token_type": "bearer"}
    except:
        raise HTTPException(status_code=422, detail="Unprocessable Data!")            

@app.get("/account_info")
def authenticate(current_user: str = Depends(get_current_user)):
    return {SUCCESS:True,RESULT:getUserInfo(current_user)}

@app.post("/create_bot")
def createBot(data:ChatBotCreationModel,current_user: str = Depends(get_current_user)):
    try:
        botID=createChatBot(current_user,data.chatBotName)   
        return {SUCCESS:True,CHATBOT_ID:botID}
    except:
        raise HTTPException(status_code=404, detail="Something Went wrong")
        
@app.get("/my_chatbots")
def myChatbots(current_user: str = Depends(get_current_user)):
    try:
        return {SUCCESS:True, CHATBOT_LIST: myChatBotsList(current_user)}
    except:
        return {SUCCESS:False}
    
@app.post("/load_chatbot_info")
def myChatbots(data:BaseChatBotModel,current_user: str = Depends(get_current_user)):
    try:
        return {SUCCESS:True, RESULT: getChatBotInfo(current_user,data.botID)}
    except:
        return {SUCCESS:False}

@app.post("/load_chatbot_content")    
def myChatbotsContent(data:BaseChatBotModel,current_user: str = Depends(get_current_user)):
    try:
        return {SUCCESS:True, RESULT: getContentMappingList(current_user,data.botID)}
    except:
        return {SUCCESS:False}
        
        
@app.post("/fetch_urls")
def fetchURLs(data:URLModel,current_user: str = Depends(get_current_user)):
    try:
        mapping=get_all_urls_mapping(data.url,max_depth=5)
        contentMappingList=get_filtered_content_mapping(current_user,data.botID,mapping)
        return {SUCCESS:True, RESULT:contentMappingList }
    except:
        raise HTTPException(status_code=404, detail="Something Went wrong")
    
    
@app.post("/add_url")
def fetchURLs(data:URLListModel,current_user: str = Depends(get_current_user)):
    try:
        mapping=get_url_list_mapping(data.urls)
        return {SUCCESS:True, RESULT:get_filtered_content_mapping(current_user,data.botID,mapping)}
    except:
        raise HTTPException(status_code=404, detail="Something Went wrong")
   

@app.post("/save_text")
def fetchURLs(data:TextModel,current_user: str = Depends(get_current_user)):
    try:
        content=saveText(current_user,data.botID,data.text)
        return {SUCCESS:True, RESULT:content}
    except:
        raise HTTPException(status_code=400, detail="Something Went wrong")
    

@app.post("/load_content")
def fetchURLs(data:ContentModel):
    try:
        return {SUCCESS:True, RESULT:getContent(data.contentID)}
    except:
        raise HTTPException(status_code=404, detail="Something Went wrong")
    
@app.post("/train_chatbot")
def train_model(data:TrainingModel,background_tasks: BackgroundTasks,current_user: str = Depends(get_current_user)):
    newlyAddedUrl = []
    if(len(data.data))<1:
        return {SUCCESS:False,RESULT:"Can't train on empty"}
    
    for item in reversed(data.data):
        if item[SOURCE_TYPE] == URL and item[STATUS] == NEWLY_ADDED:
            newlyAddedUrl.append(item(SOURCE))
            data.data.remove(item)    
            
    filtered_mapping = get_filtered_content_mapping(current_user, data.botID, get_url_list_mapping(newlyAddedUrl))    
    final_mapping= data.data + filtered_mapping
    
    getChatBotsCollection().update_one({USER_ID: current_user, CHATBOT_ID: data.botID}, {"$set": {CONTENT_LIST: final_mapping,CHATBOT_STATUS: TRAINING,LAST_UPDATED:datetime.now()}})
    updateChatBotStatus(current_user,data.botID,TRAINING)
    def train_async():
        try:
            trainChatBot(data.botID,final_mapping)
            for item in final_mapping:
                item[STATUS] = TRAINED
            getChatBotsCollection().update_one({USER_ID: current_user, CHATBOT_ID: data.botID}, {"$set": {CONTENT_LIST: final_mapping,CHATBOT_STATUS: TRAINED,LAST_UPDATED:datetime.now()}})
            updateChatBotStatus(current_user,data.botID,TRAINED)
        except:
            getChatBotsCollection().update_one({USER_ID: current_user, CHATBOT_ID: data.botID}, {"$set": {CHATBOT_STATUS: UNTRAINED,LAST_UPDATED:datetime.now()}})
            updateChatBotStatus(current_user,data.botID,UNTRAINED)
            
        
    background_tasks.add_task(train_async)
    return {SUCCESS:True,RESULT:"Chatbot is training, Please Wait"}

@app.post("/reply")
def reply(reply:ReplyModel):
    history=[]
    for item in reply.history:
        history.append((item[0],item[1]))
    chat_reply=replyToQuery(reply.botID,reply.query,history)
    return {SUCCESS:True,RESULT:{QUERY:reply.query,REPLY:chat_reply}}

@app.post("/update_chatbot_name")
def updateName(data:ChatBotNameChangeModel,current_user: str = Depends(get_current_user)):
    try:
        updateChatbotName(current_user,data.botID,data.chatBotName)
        return {SUCCESS:True}
    except:
        return {SUCCESS:False,ERROR:"Something went wrong, Try Again!"}