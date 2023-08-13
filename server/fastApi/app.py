from fastapi import Depends, FastAPI, HTTPException
from server.fastApi.modules.databaseManagement import createUserIfNotExist
from server.fastApi.modules.firebase_verification import  generate_JWT_Token, get_current_user, verifyFirebaseLogin
from src.DataBaseConstants import RESULT, SUCCESS
from starlette.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

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
    
@app.post("/authenticate")
def authenticate(data:AuthenticationModel):
    decodedToken=verifyFirebaseLogin(data.token)
    try:
        uid = decodedToken.get('uid')
        email=decodedToken.get('email')
        createUserIfNotExist(uid,email)
        jwt_token=generate_JWT_Token(uid)
        return {"access_token": jwt_token, "token_type": "bearer"}
    except:
        raise HTTPException(status_code=422, detail="Unprocessable Data!")            
    
@app.get("/api/my-chatbots")
def myChatbots(current_user: str = Depends(get_current_user)):
    return {"user":current_user}
        
    