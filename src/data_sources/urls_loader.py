from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin,urlunparse
from langchain.docstore.document import Document
from server.fastApi.modules.databaseManagement import getContentMappingList, insertContentListInBotCollection, storeContentList
from src.DataBaseConstants import SOURCE,SOURCE_TYPE, URL
from src.data_sources.utils import generateContentItem, generateContentMappingItem
import uuid
import re
import cloudscraper
from src.logger.logger import GlobalLogger
import concurrent.futures

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

def remove_query_parameters(url):
    parsed_url = urlparse(url)
    # Return the URL without query parameters or fragment
    return urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, "", "", ""))


def fetch_url_content(url, base_url, base_netloc):
    scraper = cloudscraper.create_scraper()
    new_urls = []
    try:
        response = scraper.head(url)
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            return None, []

        response = scraper.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "lxml")
            for link in soup.find_all("a", href=True):
                new_url = urljoin(base_url, link["href"])
                cleaned_url = remove_query_parameters(new_url)  # Clean the URL before adding
                parsed_url = urlparse(cleaned_url)
                if parsed_url.netloc == base_netloc and not parsed_url.fragment:
                    new_urls.append(cleaned_url)
            page_text = ' '.join(soup.stripped_strings)
            return page_text, new_urls
    except Exception as e:
        # Handle exceptions as needed
        print(f"Error fetching URL: {url}")
        print(e)
        return None, []

def get_all_urls_mapping(base_url, max_depth=5):
    visited_urls = set()
    urls_to_visit = [(base_url, 1)]
    url_text_mapping = {}
    base_netloc = urlparse(base_url).netloc

    with concurrent.futures.ThreadPoolExecutor() as executor:
        while urls_to_visit and len(visited_urls) < 100:
            current_urls = [url for url, depth in urls_to_visit if depth <= max_depth]
            current_depths = [depth for url, depth in urls_to_visit if depth <= max_depth]
            urls_to_visit = [item for item in urls_to_visit if item[0] not in current_urls]

            # Fetch content in parallel
            results = executor.map(fetch_url_content, current_urls, [base_url]*len(current_urls), [base_netloc]*len(current_urls))

            for url, depth, result in zip(current_urls, current_depths, results):
                if result is None:
                    continue
                page_text, new_urls = result
                if page_text:
                    print(url)
                    visited_urls.add(url)
                    url_text_mapping[url] = page_text
                    for new_url in new_urls:
                        if new_url not in visited_urls:
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
                