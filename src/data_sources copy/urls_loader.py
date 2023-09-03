from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from langchain.docstore.document import Document
from server.fastApi.modules.databaseManagement import getContentMappingList, insertContentListInBotCollection, storeContentList
from src.DataBaseConstants import SOURCE,SOURCE_TYPE, URL
from src.data_sources.utils import generateContentItem, generateContentMappingItem
import uuid
import re
import cloudscraper
from src.logger.logger import GlobalLogger

def get_url_list_mapping(urls):
    mappings={}
    scraper = cloudscraper.create_scraper() 
    for url in urls:
        response = scraper.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "lxml")
            # Store the text content associated with the current URL
            mappings[url]=' '.join(soup.stripped_strings)
    return mappings

def isValidUrl(url):
    pattern = r'^(https?:\/\/)([\da-z.-]+)\.([a-z]{2,6})([\/\w .-]*)*\/?$'
    return bool(re.match(pattern, url))

def get_all_urls_mapping(base_url, max_depth=5):
    visited_urls = set()
    urls_to_visit = [(base_url, 1)]  # Tuple with URL and depth
    url_text_mapping = {}  # Store URL and its associated text content
    scraper = cloudscraper.create_scraper() 
    base_netloc = urlparse(base_url).netloc 
    while urls_to_visit and len(visited_urls)<100:
        url, depth = urls_to_visit.pop(0)
        if url in visited_urls or depth > max_depth:
            continue
        try:
            response = scraper.head(url)
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                # Skip non-HTML URLs
                continue
            
            response = scraper.get(url)
            if response.status_code == 200:
                visited_urls.add(url)
                soup = BeautifulSoup(response.content, "lxml")

                # Find and process all anchor tags (links) and their text content
                for link in soup.find_all("a", href=True):
                    new_url = urljoin(base_url, link["href"])
                    parsed_url = urlparse(new_url)
                    if parsed_url.netloc == base_netloc and not parsed_url.fragment and isValidUrl(new_url):
                        urls_to_visit.append((new_url, depth + 1))

                # Store the text content associated with the current URL
                page_text = ' '.join(soup.stripped_strings)
                url_text_mapping[url] = page_text
        except Exception as e:
            GlobalLogger().error(f"Error fetching URL: {url}")
            GlobalLogger().error(e)

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
                