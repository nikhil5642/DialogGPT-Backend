import os
#from langchain.vectorstores import Pinecone
from langchain import PromptTemplate
from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain.embeddings.openai import OpenAIEmbeddings
#import pinecone
from src.training.train_model import OPENAI_API_KEY
from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from langchain.vectorstores import Chroma

text_field = "text"
condense_prompt= '''Given the following conversation and a follow up question'

        Chat History:
        {chat_history}
        Follow Up Input: {question}'''

qa_prompt = '''You are a helpful AI customer support agent running on top of this website. Use the following pieces of context to answer the question at the end.
If you don't know the answer, just share our contact details.
Feel free to share the links, url's and other things within the context. 

{context}

Question: {question}
Helpful answer in markdown:'''


# pinecone.init(api_key=PINECONE_API_KEY,environment=PINECONE_ENV)   

def replyToQuery(botID,query,chat_history):    
    QA_PROMPT = PromptTemplate(template=qa_prompt, input_variables=["context", "question"])
    CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(condense_prompt)
    db = Chroma(persist_directory=os.path.abspath("./Database/chatbot_embeddings/"+botID),embedding_function=OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY))
    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
    llm = ChatOpenAI(model_name='gpt-3.5-turbo-16k',temperature=0,openai_api_key=OPENAI_API_KEY)
    chatbot = ConversationalRetrievalChain.from_llm(
                    llm=llm,
                    retriever=db.as_retriever(), 
                    condense_question_prompt=CONDENSE_QUESTION_PROMPT,
                    memory=memory,
                    combine_docs_chain_kwargs={'prompt':QA_PROMPT})
    result = chatbot({"question": query, "chat_history": chat_history})
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
