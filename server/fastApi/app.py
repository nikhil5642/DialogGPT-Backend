from fastapi import Depends, FastAPI, HTTPException
from server.fastApi.modules.databaseManagement import createChatBot, createUserIfNotExist, getContentList, insertContentListInBotCollection, myChatBotsList, storeContentList
from server.fastApi.modules.firebase_verification import  generate_JWT_Token, get_current_user, verifyFirebaseLogin
from src.DataBaseConstants import RESULT, SOURCE, SOURCE_TYPE, SUCCESS,CHATBOT_LIST, URL
from starlette.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from src.data_sources.urls_loader import get_all_urls_mapping, url_mappings_to_storable_content

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
class FetchURLModel(BaseModel):
    url:str
    botID:str

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

@app.get("/createBot")
def createBot(current_user: str = Depends(get_current_user)):
    try:
        botID=createChatBot(current_user)   
        return {SUCCESS:True,botID:botID}
    except:
        raise HTTPException(status_code=404, detail="Something Went wrong")
        
@app.get("/my_chatbots")
def myChatbots(current_user: str = Depends(get_current_user)):
    try:
        return {SUCCESS:True, CHATBOT_LIST: myChatBotsList(current_user)}
    except:
        return {SUCCESS:False}
        
@app.post("/fetch_urls")
def fetchURLs(data:FetchURLModel,current_user: str = Depends(get_current_user)):
    try:
        mapping=get_all_urls_mapping(data.url,max_depth=1)
        current_collections=getContentList(current_user,data.botID)
        
        existing_urls = {item[SOURCE] for item in current_collections if item[SOURCE_TYPE] == URL}
        filtered_mapping = {key: value for key, value in mapping.items() if key not in existing_urls}
        
        contentList,contentMappingList=url_mappings_to_storable_content(filtered_mapping)
        storeContentList(contentList)
        insertContentListInBotCollection(data.botID,contentMappingList)
        return {SUCCESS:True, RESULT:contentMappingList}
    except:
        raise HTTPException(status_code=404, detail="Something Went wrong")
    
    
    
    
  