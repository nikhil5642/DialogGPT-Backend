from server.fastApi.modules.databaseManagement import getContentMappingList, insertContentListInBotCollection, storeContent, updateContent
from src.DataBaseConstants import SOURCE, SOURCE_TYPE,TEXT,CONTENT_ID
import uuid

from src.data_sources.utils import generateContentMappingItem


def saveText(uid:str,botID:str,text:str):
    contentList=getContentMappingList(uid,botID)
    content = next((item for item in contentList if item[SOURCE_TYPE] == TEXT), None)
    if content is None:
        content=generateContentMappingItem(str(uuid.uuid4()),TEXT,TEXT,text)
        storeContent(content[CONTENT_ID],text)
        contentList.append(content)
        insertContentListInBotCollection(uid,botID,contentList)
    else:
        updateContent(uid,botID,content[CONTENT_ID],text)
    return content