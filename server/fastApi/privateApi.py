from typing import List, Literal, Optional
from fastapi import Depends, FastAPI, HTTPException, BackgroundTasks, Request
from DataBase.MongoDB import getChatBotsCollection
from server.fastApi.modules.databaseManagement import createChatBot, createUserIfNotExist, get_subscription_plan, getChatBotInfo, getChatInterface, getChatModel, getContent, getContentMappingList, getMessageCredits, getRemainingMessageCredits, getUserInfo, getUserChatBotInfo, updateChatBotStatus, updateChatInterface, updateChatModel, updateChatbotName, updateMessageUsed
from server.fastApi.modules.firebase_verification import  generate_JWT_Token, get_current_user, verifyFirebaseLogin
from server.fastApi.modules.stripeSubscriptionMangement import createStripeCheckoutSession, manageWebhook
from src.DataBaseConstants import CHATBOT_ID, CHATBOT_STATUS, CONTENT_LIST, LAST_UPDATED, MESSAGE_CREDITS, MESSAGE_USED, RESULT, SOURCE, SOURCE_TYPE, STATUS, SUCCESS,CHATBOT_LIST, TRAINED, URL,NEWLY_ADDED, USER_ID,TRAINING,QUERY,REPLY,ERROR,UNTRAINED,CHATBOT_LIMIT
from starlette.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from src.data_sources.text_loader import saveText
from datetime import datetime
from src.data_sources.urls_loader import get_all_urls_mapping, get_filtered_content_mapping, get_url_list_mapping, isValidUrl
from src.scripts.scrapper import BrowserPool,LazyBrowserPool
from src.training.consume_model import replyToQuery
from src.training.train_model import trainChatBot
import atexit

privateApi = FastAPI()

def get_browser_pool():
    return LazyBrowserPool.get_instance()

origins = ["http://localhost:3000",
           "https://www.dialoggpt.io",
           "https://dialoggpt.io"]

privateApi.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@privateApi.get("/")
async def root():
    return {"message": "Hello Bigger Applications!"}

def cleanup():
    get_browser_pool().shutdown()

@privateApi.on_event("startup")
async def startup_event():
    get_browser_pool()
    
@privateApi.on_event("shutdown")
async def shutdown_event():
    cleanup()
    
atexit.register(cleanup)
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

class ChatMessageModel(BaseModel):
    id: int
    text: str
    type: Literal["incoming", "outgoing"]

class ReplyModel(BaseChatBotModel):
    query:str
    history:List[ChatMessageModel]
    
class SubscriptionModel(BaseModel):
    planId: str

class ChatBotInterfaceModel(BaseChatBotModel):
    initialMessage: str
    quickPrompts: str
    theme: str
    profilePicture: Optional[str]
    userMsgColor: str
    displayName: str
    chatIcon: Optional[str]
    chatBubbleColor: str
    
class ChatBotModelModel(BaseChatBotModel):
    prompt: str
    modelVersion: str
    temperature: float
        

@privateApi.post("/authenticate")
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

@privateApi.get("/account_info")
def accountInfo(current_user: str = Depends(get_current_user)):
    return {SUCCESS:True,RESULT:getUserInfo(current_user)}

@privateApi.get("/message_credits")
def messageCredits(current_user: str = Depends(get_current_user)):
    return {SUCCESS:True,RESULT:getRemainingMessageCredits(current_user)}

@privateApi.post("/create_bot")
def createBot(data:ChatBotCreationModel,current_user: str = Depends(get_current_user)):
    try:
        botID=createChatBot(current_user,data.chatBotName)   
        return {SUCCESS:True,CHATBOT_ID:botID}
    except HTTPException as e:  # Catch the specific exception
        raise e  # Re-raise the caught exception
    except:
        raise HTTPException(status_code=501, detail="Something Went wrong")
        
@privateApi.get("/my_chatbots")
def myChatbots(current_user: str = Depends(get_current_user)):
    try:
        chatbot_list,chatbot_limit=getUserChatBotInfo(current_user)
        return {SUCCESS:True, CHATBOT_LIST: chatbot_list,CHATBOT_LIMIT:chatbot_limit}
    except:
        return {SUCCESS:False}
    
@privateApi.post("/load_chatbot_info")
def myChatbotInfo(data:BaseChatBotModel,current_user: str = Depends(get_current_user)):
    try:
        return {SUCCESS:True, RESULT: getChatBotInfo(current_user,data.botID)}
    except:
        return {SUCCESS:False}

@privateApi.post("/load_chatbot_content")    
def myChatbotsContent(data:BaseChatBotModel,current_user: str = Depends(get_current_user)):
    try:
        return {SUCCESS:True, RESULT: getContentMappingList(current_user,data.botID)}
    except:
        return {SUCCESS:False}
        
        
@privateApi.post("/fetch_urls")
async def fetchURLs(data:URLModel,current_user: str = Depends(get_current_user), browser_pool: BrowserPool = Depends(get_browser_pool)):
    if not isValidUrl(data.url):
        raise HTTPException(status_code=501, detail="Invalid URL")
    
    try:
        mapping= get_all_urls_mapping(data.url,browser_pool,max_depth=5)
        contentMappingList=get_filtered_content_mapping(current_user,data.botID,mapping)
        return {SUCCESS:True, RESULT:contentMappingList }
    except:
        raise HTTPException(status_code=501, detail="Something Went wrong")
    
    
@privateApi.post("/add_url")
def fetchURLs(data:URLListModel,current_user: str = Depends(get_current_user)):
    try:
        mapping=get_url_list_mapping(data.urls)
        return {SUCCESS:True, RESULT:get_filtered_content_mapping(current_user,data.botID,mapping)}
    except:
        raise HTTPException(status_code=404, detail="Something Went wrong")
   

@privateApi.post("/save_text")
def fetchURLs(data:TextModel,current_user: str = Depends(get_current_user)):
    try:
        content=saveText(current_user,data.botID,data.text)
        return {SUCCESS:True, RESULT:content}
    except:
        raise HTTPException(status_code=400, detail="Something Went wrong")
    

@privateApi.post("/load_content")
def fetchURLs(data:ContentModel):
    try:
        return {SUCCESS:True, RESULT:getContent(data.contentID)}
    except:
        raise HTTPException(status_code=404, detail="Something Went wrong")
    
@privateApi.post("/train_chatbot")
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

@privateApi.post("/reply")
def reply(reply:ReplyModel):
    try:
        uid= getChatBotsCollection().find_one({CHATBOT_ID:reply.botID}).get(USER_ID)
        userDoc= getUserInfo(uid)
        msgCredits=getMessageCredits(userDoc)[MESSAGE_CREDITS]
        if(msgCredits>0):
            chat_reply=replyToQuery(reply.botID,reply.query,reply.history[-5:])
            updateMessageUsed(uid,userDoc.get(MESSAGE_USED,0)+1)
        else:
            chat_reply="Credit Limit Exceeded"
        return {SUCCESS:True,RESULT:{QUERY:reply.query,REPLY:chat_reply}}
    except:
         raise HTTPException(status_code=501, detail="Something went wrong, Try Again!")
    
@privateApi.post("/update_chatbot_name")
def updateName(data:ChatBotNameChangeModel,current_user: str = Depends(get_current_user)):
    try:
        updateChatbotName(current_user,data.botID,data.chatBotName)
        return {SUCCESS:True}
    except:
         raise HTTPException(status_code=501, detail="Something went wrong, Try Again!")

@privateApi.post("/fetch_chatbot_model")
def fetchChatbotModel(data: BaseChatBotModel, _: str = Depends(get_current_user)):
    try:
        return {SUCCESS:True,RESULT:getChatModel(data.botID)}
    except:
         raise HTTPException(status_code=501, detail="Something went wrong, Try Again!")

@privateApi.post("/update_chatbot_model")
def updateChatbotModel(data:ChatBotModelModel,current_user: str = Depends(get_current_user)):
    try:
        updateChatModel(current_user,data.botID,data.prompt,data.modelVersion,data.temperature)
        return {SUCCESS:True}
    except:
         raise HTTPException(status_code=501, detail="Something went wrong, Try Again!")


@privateApi.post("/fetch_chatbot_interface")
def fetchChatBotInterface(data: BaseChatBotModel):
    try:
        return {SUCCESS:True,RESULT:getChatInterface(data.botID)}
    except:
         raise HTTPException(status_code=501, detail="Something went wrong, Try Again!")

@privateApi.post("/update_chatbot_interface")
def updateChatBotInterface(data:ChatBotInterfaceModel,current_user: str = Depends(get_current_user)):
    try:
        updateChatInterface(current_user,data.botID,data.initialMessage,data.quickPrompts,data.theme,data.profilePicture,data.userMsgColor,data.displayName,data.chatIcon,data.chatBubbleColor)
        return {SUCCESS:True}
    except:
         raise HTTPException(status_code=501, detail="Something went wrong, Try Again!")


@privateApi.get("/current_subscription_plan")
def subscriptionStatus(current_user: str = Depends(get_current_user)):
    return {SUCCESS:True,RESULT:get_subscription_plan(current_user)}

      
@privateApi.post("/create_checkout_session")
def createCheckoutSessionApi(data:SubscriptionModel,current_user: str = Depends(get_current_user)):
    try:
        session =createStripeCheckoutSession(current_user,data.planId)
        return {SUCCESS:True, RESULT: session}
    except:
        raise HTTPException(status_code=501, detail="Something went wrong, Try Again!")
      

@privateApi.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    try:
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        return  manageWebhook(payload,sig_header)
    except:
        raise HTTPException(status_code=501, detail="Something went wrong, Try Again!")
    