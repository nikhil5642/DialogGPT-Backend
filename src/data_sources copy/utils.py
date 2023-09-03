from src.DataBaseConstants import CONTENT_ID, CONTENT,SOURCE,SOURCE_TYPE,LAST_UPDATED,CHAR_COUNT,STATUS,UNTRAINED
from datetime import datetime

def generateContentMappingItem(contentID,source,source_type,value):
    return {CONTENT_ID:contentID, SOURCE:source,SOURCE_TYPE:source_type,CHAR_COUNT:len(value),LAST_UPDATED:datetime.now(),STATUS:UNTRAINED}

def generateContentItem(contentID,value):
    return {CONTENT_ID:contentID, CONTENT:value,LAST_UPDATED:datetime.now()}
