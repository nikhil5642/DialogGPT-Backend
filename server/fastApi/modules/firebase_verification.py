import firebase_admin
from firebase_admin import auth,credentials
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os

SECRET_KEY = "69e62f451956d5f6f3c6047c6d6cd82381785933"  # Replace with your own secret key
ALGORITHM = "HS256"

cred = credentials.Certificate(os.path.abspath("./DataBase/firebase-chatbot-admin.json"))
firebase_admin.initialize_app(cred)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_jwt_token(data: dict) -> str:
    to_encode = data.copy()
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verifyFirebaseLogin(firebase_token:str):
    try:
       return auth.verify_id_token(firebase_token)
    except:
        raise HTTPException(status_code=401, detail="Unauthorised!")
def generate_JWT_Token(uid: str):
    try:
        # Decode the Firebase ID token
        data = {
            "sub": uid,
            "scope": "me",
            "iss": "fastapi-jwt",
        }
        jwt_token = create_jwt_token(data)
        return jwt_token
    
    except:
        raise HTTPException(status_code=400, detail="Error decoding or encoding tokens")
    
    
    
async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = payload.get("sub")
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
        return user
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )