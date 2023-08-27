import os
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.docstore.document import Document
from DataBase.MongoDB import getContentStoreCollection
from src.DataBaseConstants import CHATBOT_ID, SOURCE,SOURCE_TYPE,CONTENT_ID,CONTENT
# import pinecone
from langchain.vectorstores import Chroma
from uuid import uuid4
from tqdm.auto import tqdm
import shutil

from src.logger.logger import GlobalLogger

# PINECONE_API_KEY = "87a0ff8e-534a-47cc-97bc-4ba9aac009e0"
OPENAI_API_KEY='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'

# PINECONE_ENV = "us-west4-gcp-free"

def getDocumentsList(contentIDList):
    idList=[item[CONTENT_ID] for item in contentIDList]
    contentMapping={}
    for content in getContentStoreCollection().find({CONTENT_ID: {'$in': idList}}):
        contentMapping[content[CONTENT_ID]]=content[CONTENT]
        
    docList=[]
    for item in contentIDList:
        docList.append(Document(page_content=contentMapping[item[CONTENT_ID]], metadata={SOURCE: item[SOURCE],SOURCE_TYPE:item[SOURCE_TYPE]}))
    return docList

def trainChatBot(botID,contentIDList):
    persist_directory=os.path.abspath("./Database/chatbot_embeddings/"+botID)
    if os.path.exists(persist_directory):
        shutil.rmtree(persist_directory)
    docs=getDocumentsList(contentIDList)
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    chunks = text_splitter.split_documents(docs)
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)
    db = Chroma.from_documents(chunks, embeddings,persist_directory=persist_directory)
    db.persist()
    GlobalLogger().debug("Chatbot Trained Successfully "+botID)
        

# def trainChatBot(botID,contentIDList):
#     docs=getDocumentsList(contentIDList)
#     index=createPineConeIndex(botID)
#     # split the documents into chunks
#     text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
#     chunks = text_splitter.split_documents(docs)
#     # select which embeddings we want to use
#     embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

#     batch_limit = 100
#     texts = []
#     metadatas = []
    
#     for record in tqdm(chunks):
#         # first get metadata fields for this record
#         texts.append(record.page_content)
#         metadatas.append({"text":record.page_content,**record.metadata})
#         # if we have reached the batch_limit we can add texts
#         if len(texts) >= batch_limit:
#             ids = [str(uuid4()) for _ in range(len(texts))]
#             embeds = embeddings.embed_documents(texts)
#             index.upsert(vectors=zip(ids, embeds, metadatas))
#             texts = []
#             metadatas = []

#     if len(texts) > 0:
#         ids = [str(uuid4()) for _ in range(len(texts))]
#         embeds = embeddings.embed_documents(texts)
#         index.upsert(vectors=zip(ids, embeds, metadatas))  
        
#     GlobalLogger().debug("Chatbot Trained Successfully "+CHATBOT_ID)
    

# def createPineConeIndex(index_name:str):
#     pinecone.init(api_key=PINECONE_API_KEY,environment=PINECONE_ENV)    
#     if index_name in pinecone.list_indexes():
#         pinecone.delete_index(index_name)
#     pinecone.create_index(
#         name=index_name,
#         metric='cosine',
#         dimension=1536  # 1536 dim of text-embedding-ada-002
#     )
#     index = pinecone.Index(index_name)   
#     return index

 
