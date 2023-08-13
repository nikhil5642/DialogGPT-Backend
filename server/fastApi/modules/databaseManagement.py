from DataBase.MongoDB import getUsersCollection
from src.DataBaseConstants import EMAIL_ID, USER_ID
from src.logger.logger import GlobalLogger


def createUserIfNotExist(uid:str,email:str):
    if not getUsersCollection().find_one({USER_ID:uid}):
        getUsersCollection().insert_one({USER_ID:uid,EMAIL_ID:email})
        GlobalLogger.debug("User created successfully UID: "+uid)
        

     
         
    
