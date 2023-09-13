
from fastapi import FastAPI, HTTPException
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from server.fastApi.modules.databaseManagement import getChatInterface

from src.DataBaseConstants import RESULT, SUCCESS

publicApp = FastAPI()

publicApp.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BaseChatBotModel(BaseModel):
    botID:str

@publicApp.post("/fetch_chatbot_interface")
def fetchChatBotInterface(data: BaseChatBotModel):
    try:
        return {SUCCESS:True,RESULT:getChatInterface(data.botID)}
    except:
         raise HTTPException(status_code=501, detail="Something went wrong, Try Again!")
