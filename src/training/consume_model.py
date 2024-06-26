import os
import time
#from langchain.vectorstores import Pinecone
from langchain import LLMChain, PromptTemplate
from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain.embeddings.openai import OpenAIEmbeddings
from server.fastApi.modules.databaseManagement import getChatModel
from src.DataBaseConstants import MODEL_VERSION, PROMPT, TEMPERATURE
#import pinecone
from src.training.train_model import OPENAI_API_KEY
from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from langchain.vectorstores import Chroma
text_field = "text"
condense_prompt="""Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question, in its original language.
------------------------
Chat History:
{chat_history}
------------------------
Follow Up Input: {question}
Standalone question:"""

qa_prompt = ''' 
------------------------
Context: 

{context}

------------------------
Question: {question}
Helpful answer in markdown:'''


# pinecone.init(api_key=PINECONE_API_KEY,environment=PINECONE_ENV)   

def replyToQuery(model,botID,query,chat_history):   
    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
    for chat in chat_history:
        if chat.type=="incoming":
            memory.chat_memory.add_ai_message(chat.text)
        else:
            memory.chat_memory.add_user_message(chat.text)
            
    temp_qa_prompt= model[PROMPT]+qa_prompt
    QA_PROMPT = PromptTemplate(template=temp_qa_prompt, input_variables=["context", "question"])
    CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(condense_prompt)
    db = Chroma(persist_directory=os.path.abspath("./Database/chatbot_embeddings/"+botID),embedding_function=OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY))
    
    llm = ChatOpenAI(model_name=model[MODEL_VERSION],temperature=model[TEMPERATURE],openai_api_key=OPENAI_API_KEY)
    chatbot = ConversationalRetrievalChain.from_llm(
                    llm=llm,
                    retriever=db.as_retriever(search_type="mmr", search_kwargs={"k":2}), 
                    condense_question_prompt=CONDENSE_QUESTION_PROMPT,
                    memory=memory,
                    combine_docs_chain_kwargs={'prompt':QA_PROMPT})
    result = chatbot({"question": query})
    return result["answer"]


# def replyToQuery(botID,query,chat_history):    
#     QA_PROMPT = PromptTemplate(template=qa_prompt, input_variables=["context", "question"])
#     CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(condense_prompt)
    
#     index = pinecone.Index(botID)
#     vectorstore = Pinecone(
#         index, OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY).embed_query, text_field
#     )
#     memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
#     llm = ChatOpenAI(model_name='gpt-3.5-turbo-16k',temperature=0,openai_api_key=OPENAI_API_KEY)
#     chatbot = ConversationalRetrievalChain.from_llm(
#                     llm=llm,
#                     retriever=vectorstore.as_retriever(), 
#                     condense_question_prompt=CONDENSE_QUESTION_PROMPT,
#                     memory=memory,
#                     combine_docs_chain_kwargs={'prompt':QA_PROMPT})
#     result = chatbot({"question": query, "chat_history": chat_history})
#     return result["answer"]
