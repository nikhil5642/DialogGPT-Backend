from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin,urlunparse
from langchain.docstore.document import Document
from DataBase.MongoDB import getChatBotsCollection
from server.fastApi.modules.databaseManagement import getContentMappingList, insertContentListInBotCollection, storeContentList,deleteContentID
from src.DataBaseConstants import CHATBOT_ID, CONTENT_ID, CONTENT_LIST, SOURCE,SOURCE_TYPE, URL, USER_ID
from src.data_sources.utils import generateContentItem, generateContentMappingItem
import uuid
import re
import cloudscraper
from src.logger.logger import GlobalLogger
import concurrent.futures
from threading import Lock
from src.scripts.scrapper import MAX_THREADS

def get_url_list_mapping(urls,browser_pool):
    mappings={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        # Fetch content in parallel
        results = executor.map(load_page_source, urls, [browser_pool]*len(urls)) # Use original base_url for joining
        for url, result in zip(urls, results):
            if result is None:
                continue
            page_source= result
            soup = BeautifulSoup(page_source, "lxml")
            page_text = ' '.join(soup.stripped_strings)
            
            if page_text:
                mappings[url] = page_text
                    
    return mappings

def isValidUrl(url):
    pattern = r'^(https?:\/\/)([\da-z.-]+)\.([a-z]{2,6})([\/\w .-]*)*\/?$'
    return bool(re.match(pattern, url))

def remove_query_parameters(url):
    parsed_url = urlparse(url)
    # Return the URL without query parameters or fragment
    return urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, "", "", ""))

def resolve_redirects(url):
    """
    Resolve any redirects and return the final URL using cloudscraper.
    """
    scraper = cloudscraper.create_scraper()
    try:
        response = scraper.get(url, allow_redirects=True)
        return response.url
    except Exception as e:
        GlobalLogger().error(f"Error resolving redirects for URL: {url}")
        GlobalLogger().error(e)
        return url
    
def fetch_url_content(url, base_url, browser_pool):
    new_urls = []
    try:
        page_source = load_page_source(url, browser_pool)
        if not page_source:
            return None, []
        
        soup = BeautifulSoup(page_source, "lxml")
        for link in soup.find_all("a", href=True):
            new_url = urljoin(base_url, link["href"])
            cleaned_url = remove_query_parameters(new_url)
            if cleaned_url.startswith(base_url) and not urlparse(cleaned_url).fragment:
                new_urls.append(cleaned_url)

        page_text = ' '.join(soup.stripped_strings)
        return page_text, new_urls
    except Exception as e:
        GlobalLogger().error(f"Error fetching URL: {url}")
        GlobalLogger().error(e)
        return None, []

def load_page_source(url, browser_pool):
    browser = browser_pool.get()
    browser.get(url)
    page_source = browser.page_source
    browser_pool.release(browser)
    return page_source


def get_all_urls_mapping(base_url,browser_pool, max_depth=5):
    # Resolve any redirects for the base URL to fetch the content
    resolved_url = resolve_redirects(base_url)
     # Initialize a Lock for synchronized access to urls_to_visit
    url_lock = Lock()

    visited_urls = set()
    urls_to_visit = [(resolved_url, 1)]  # Start with the resolved URL to fetch content
    url_text_mapping = {}
   
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        while urls_to_visit and len(visited_urls) < 50:
            with url_lock: 
                current_urls = [url for url, depth in urls_to_visit if depth <= max_depth]
                current_depths = [depth for url, depth in urls_to_visit if depth <= max_depth]
                # Mark current_urls as visited immediately
                visited_urls.update(current_urls)

                urls_to_visit = [item for item in urls_to_visit if item[0] not in current_urls]

            # Fetch content in parallel
            results = executor.map(fetch_url_content, current_urls, [base_url]*len(current_urls),[browser_pool]*len(current_urls)) # Use original base_url for joining

            for url, depth, result in zip(current_urls, current_depths, results):
                if result is None:
                    continue
                page_text, new_urls = result
                if page_text:
                    url_text_mapping[url] = page_text
                    for new_url in new_urls :
                        if new_url not in visited_urls and new_url not in [item[0] for item in urls_to_visit]:
                            urls_to_visit.append((new_url, depth + 1))
    return url_text_mapping


def url_mappings_to_storable_content(mapping):
    """
    Convert URL mappings to storable content.

    Parameters:
        url_mappings (str): The URL-to-text content mapping.

    Returns:
        tuple: A tuple containing two lists.
            - content_list (list of dict): List of dictionaries containing Content ID and Content text. 
              Store this in the content collection.
            - content_mapping_list (list of dict): List of dictionaries containing content information.
              This will be used to map content ID to a bot, mainly for display purposes.
    """
    
    contentList=[]
    contentMappingList=[]
    for key, value in mapping.items():
        contentID=str(uuid.uuid4())
        contentList.append(generateContentItem(contentID,value))
        contentMappingList.append(generateContentMappingItem(contentID,key,URL,value))
    return contentList,contentMappingList


def url_mappings_to_Documents(mapping):
    docsList=[]
    for key, value in mapping.items():
        docsList.append(Document(page_content=value, metadata={"source": key,"source_type":"url"}))
    return docsList

def get_filtered_content_mapping(uid:str,botID:str,mapping):
    current_collections=getContentMappingList(uid,botID)
    existing_urls = {item[SOURCE] for item in current_collections if item[SOURCE_TYPE] == URL}
    filtered_mapping = {key: value for key, value in mapping.items() if key not in existing_urls}
    contentList,contentMappingList=url_mappings_to_storable_content(filtered_mapping)
    storeContentList(contentList)
    current_collections.extend(contentMappingList)
    insertContentListInBotCollection(uid,botID,current_collections)
    return contentMappingList
        
def get_final_content_mapping(uid:str,botID:str,mapping):
    current_collections=getContentMappingList(uid,botID)
    existing_urls = {item[SOURCE] for item in current_collections if item[SOURCE_TYPE] == URL}
    filtered_mapping = {key: value for key, value in mapping.items() if key not in existing_urls}
    contentList,contentMappingList=url_mappings_to_storable_content(filtered_mapping)
    storeContentList(contentList)
    current_collections.extend(contentMappingList)
    insertContentListInBotCollection(uid,botID,current_collections)
    return current_collections
                
def update_final_mappings(uid:str,botID:str,mapping):
    removedContentId=[]
    for item in getContentMappingList(uid,botID):
        if item[SOURCE_TYPE]==URL and not any(map_item[CONTENT_ID] == item[CONTENT_ID] for map_item in mapping):
            removedContentId.append(item[CONTENT_ID])
    deleteContentID(removedContentId)   
    getChatBotsCollection().update_one({USER_ID: uid, CHATBOT_ID: botID}, {"$set": {CONTENT_LIST: mapping}})
     
     
