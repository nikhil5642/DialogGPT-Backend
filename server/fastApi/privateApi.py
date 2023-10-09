from typing import List, Literal, Optional
from fastapi import Depends, FastAPI, HTTPException, BackgroundTasks, Request
from DataBase.MongoDB import getChatBotsCollection
from server.fastApi.modules.databaseManagement import createChatBot, createUserIfNotExist, get_subscription_plan, getChatBotInfo, getChatInterface, getChatModel, getContent, getContentMappingList, getMessageCredits, getRemainingMessageCredits, getUserInfo, getUserChatBotInfo, updateChatBotStatus, updateChatInterface, updateChatModel, updateChatbotName, updateMessageUsed,deleteChatbot
from server.fastApi.modules.firebase_verification import  generate_JWT_Token, get_current_user, verifyFirebaseLogin
from server.fastApi.modules.stripeSubscriptionMangement import createStripeCheckoutSession, manageWebhook, subscription_management_url
from src.DataBaseConstants import CHATBOT_ID, CHATBOT_STATUS, CONTENT_ID, GPT_3_5_TURBO, GPT_4, MESSAGE_CREDITS, MESSAGE_USED, MODEL_VERSION, REMOVING, RESULT, SOURCE, SOURCE_TYPE, STATUS, SUCCESS,CHATBOT_LIST, TRAINED, URL,NEWLY_ADDED, USER_ID,TRAINING,QUERY,REPLY,UNTRAINED,CHATBOT_LIMIT
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from src.data_sources.text_loader import saveText
from src.data_sources.urls_loader import get_all_urls_mapping, get_filtered_content_mapping, get_url_list_mapping, isValidUrl, update_final_mappings
from src.scripts.scrapper import BrowserPool,LazyBrowserPool
from src.training.consume_model import replyToQuery
from src.training.train_model import trainChatBot

privateApi = FastAPI()

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
async def fetchURLs(data:URLModel,current_user: str = Depends(get_current_user)):
    if not isValidUrl(data.url):
        raise HTTPException(status_code=501, detail="Invalid URL")
    
    try:
        mapping= await get_all_urls_mapping(data.url,max_depth=5)
        contentMappingList=get_filtered_content_mapping(current_user,data.botID,mapping)
        return {SUCCESS:True, RESULT:contentMappingList }
    except:
        raise HTTPException(status_code=501, detail="Something Went wrong")
    
    
@privateApi.post("/add_url")
async def fetchURLs(data:URLListModel,current_user: str = Depends(get_current_user)):
    try:
        mapping=await get_url_list_mapping(data.urls)
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

async def updateURLDataAsync(data:TrainingModel,current_user: str):
    newlyAddedUrl = []
    if(len(data.data))<1:
        return {SUCCESS:False,RESULT:"Can't train on empty"}
    for item in reversed(data.data):
        if item[SOURCE_TYPE] == URL:
            if item[STATUS] == NEWLY_ADDED:
                newlyAddedUrl.append(item[SOURCE])
                data.data.remove(item)    
            elif item[STATUS] == REMOVING:
                data.data.remove(item)    
    new_url_mapping=await get_url_list_mapping(newlyAddedUrl)
    filtered_mapping = get_filtered_content_mapping(current_user, data.botID, new_url_mapping)   
    final_mapping= data.data + filtered_mapping
    update_final_mappings(current_user,data.botID,final_mapping)
    return final_mapping


@privateApi.post("/update_url_data")
async def updateURLData(data:TrainingModel,current_user: str = Depends(get_current_user)):
    final_mappings=await updateURLDataAsync(data,current_user)
    return {SUCCESS:True,RESULT:final_mappings} 

@privateApi.post("/train_chatbot")
async def train_model(data:TrainingModel,background_tasks: BackgroundTasks,current_user: str = Depends(get_current_user)):
    final_mapping=await updateURLDataAsync(data,current_user)
    updateChatBotStatus(current_user,data.botID,TRAINING)
    def train_async():
        try:
            trainChatBot(data.botID,final_mapping)
            for item in final_mapping:
                item[STATUS] = TRAINED
            updateChatBotStatus(current_user,data.botID,TRAINED)
        except:
            updateChatBotStatus(current_user,data.botID,UNTRAINED)
            
    background_tasks.add_task(train_async)
    return {SUCCESS:True,RESULT:"Chatbot is training, Please Wait"}


@privateApi.post("/reply")
def reply(reply:ReplyModel):
    try:
        uid= getChatBotsCollection().find_one({CHATBOT_ID:reply.botID}).get(USER_ID)
        userDoc= getUserInfo(uid)
        msgCredits=getMessageCredits(userDoc)[MESSAGE_CREDITS]
        model=getChatModel(reply.botID)
        print(model,GPT_3_5_TURBO,GPT_4)
        if(model[MODEL_VERSION]==GPT_3_5_TURBO and msgCredits>0):
            chat_reply=replyToQuery(model,reply.botID,reply.query,reply.history[-5:])
            updateMessageUsed(uid,userDoc.get(MESSAGE_USED,0)+1)
        elif(model[MODEL_VERSION]==GPT_4 and msgCredits>20):
            chat_reply=replyToQuery(model,reply.botID,reply.query,reply.history[-5:])
            updateMessageUsed(uid,userDoc.get(MESSAGE_USED,0)+20)
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

@privateApi.post("/delete_chatbot")
def deleteChatbotApi(data: BaseChatBotModel, current_user: str = Depends(get_current_user)):
    try:
        deleteChatbot(current_user,data.botID)
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

@privateApi.get("/manage_subscription")
def createCheckoutSessionApi(current_user: str = Depends(get_current_user)):
    try:
        url =subscription_management_url(current_user)
        return {SUCCESS:True, RESULT: url}
    except:
        raise HTTPException(status_code=501, detail="Something went wrong, Try Again!")
    

@privateApi.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    try:
        payload = await request.body()
        sig_header = request.headers.get('stripe-signature')
        return  manageWebhook(payload,sig_header)
    except HTTPException as e:  # Catch the specific exception
        raise e  # 
    except:
        raise HTTPException(status_code=501, detail="Something went wrong, Try Again!")
    
