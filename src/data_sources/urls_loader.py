import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from langchain.docstore.document import Document
from src.DataBaseConstants import CONTENT_ID, CONTENT,SOURCE,SOURCE_TYPE,LAST_UPDATED,CHAR_COUNT, URL
from datetime import datetime
import uuid

def get_all_urls_mapping(base_url, max_depth=5):
    visited_urls = set()
    urls_to_visit = [(base_url, 1)]  # Tuple with URL and depth
    url_text_mapping = {}  # Store URL and its associated text content
    
    while urls_to_visit and len(visited_urls)<100:
        url, depth = urls_to_visit.pop(0)
        print(url)
        if url in visited_urls or depth > max_depth:
            continue
        try:
            response = requests.get(url)
            if response.status_code == 200:
                visited_urls.add(url)
                soup = BeautifulSoup(response.content, "lxml")

                # Find and process all anchor tags (links) and their text content
                for link in soup.find_all("a", href=True):
                    new_url = urljoin(base_url, link["href"])
                    parsed_url = urlparse(url)
                    if parsed_url.netloc == urlparse(base_url).netloc and not parsed_url.fragment:
                        urls_to_visit.append((new_url, depth + 1))

                # Store the text content associated with the current URL
                page_text = ' '.join(soup.stripped_strings)
                url_text_mapping[url] = page_text
        except Exception as e:
            print(f"Error fetching URL: {url}")
            print(e)

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
        contentList.append({CONTENT_ID:contentID,CONTENT:value})
        contentMappingList.append({CONTENT_ID:contentID, SOURCE:key,SOURCE_TYPE:URL,CHAR_COUNT:len(value),LAST_UPDATED:datetime.now()})
    return contentList,contentMappingList


def url_mappings_to_Documents(mapping):
    docsList=[]
    for key, value in mapping.items():
        docsList.append(Document(page_content=value, metadata={"source": key,"source_type":"url"}))
    return docsList
