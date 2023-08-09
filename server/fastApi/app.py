from fastapi import FastAPI
from server.fastApi.modules.dailyChallengeManagement import getChallengeData
from server.fastApi.modules.dailyMateInXChallengeManagement import getMateInXChallengeData
from server.fastApi.modules.mobileDataLoader import getMobileItemData
from server.fastApi.modules.subscriberManagement import addUpdateSubscriber
from src.DataBaseConstants import RESULT, SUCCESS
from starlette.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import base64

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


class EmailSubscriberModel(BaseModel):
    emailId: str


@app.post("/subscribe")
async def subscribe(data: EmailSubscriberModel):
    return {SUCCESS: addUpdateSubscriber(data.emailId)}

