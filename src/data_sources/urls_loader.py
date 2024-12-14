from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urlunparse
from langchain.docstore.document import Document
import requests
from DataBase.MongoDB import getChatBotsCollection
from server.fastApi.modules.databaseManagement import (
    getContentMappingList,
    insertContentListInBotCollection,
    storeContentList,
    deleteContentID,
)
from src.DataBaseConstants import (
    CHATBOT_ID,
    CONTENT_ID,
    CONTENT_LIST,
    SOURCE,
    SOURCE_TYPE,
    URL,
    USER_ID,
)
from src.data_sources.utils import generateContentItem, generateContentMappingItem
import uuid
import re
import asyncio
import cloudscraper
from src.logger.logger import GlobalLogger
from typing import Optional, Dict, List, Tuple, Set
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urlunparse
from langchain.docstore.document import Document
import requests
import asyncio
import uuid
import re
from functools import lru_cache
from dataclasses import dataclass
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

# Constants
MAX_THREADS = 10
MAX_URLS = 50
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3


@dataclass
class ScrapingResult:
    text: str
    urls: List[str]
    success: bool
    error: Optional[str] = None


class WebScraper:
    def __init__(self):
        self.session = self._create_session()
        self.scraper = cloudscraper.create_scraper()

    def _create_session(self) -> requests.Session:
        """Create a session with retry strategy"""
        session = requests.Session()
        retry_strategy = Retry(
            total=MAX_RETRIES, backoff_factor=1, status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )
        return session

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Validate URL format"""
        pattern = r"^(https?:\/\/)([\da-z.-]+)\.([a-z]{2,6})([\/\w .-]*)*\/?$"
        return bool(re.match(pattern, url))

    @staticmethod
    def remove_query_parameters(url: str) -> str:
        """Remove query parameters from URL"""
        parsed_url = urlparse(url)
        return urlunparse(
            (parsed_url.scheme, parsed_url.netloc, parsed_url.path, "", "", "")
        )

    def resolve_redirects(self, url: str) -> str:
        """Resolve URL redirects"""
        try:
            response = self.scraper.get(
                url, allow_redirects=True, timeout=DEFAULT_TIMEOUT
            )
            return response.url
        except Exception as e:
            GlobalLogger().error(f"Error resolving redirects for URL: {url} - {str(e)}")
            return url

    @lru_cache(maxsize=100)
    def load_page_source(self, url: str) -> Optional[str]:
        """Fetch page source with caching"""
        try:
            response = self.session.get(url, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            GlobalLogger().error(f"Error fetching URL: {url} - {str(e)}")
            return None

    def fetch_url_content(self, url: str, base_url: str) -> ScrapingResult:
        """Fetch URL content and extract links with improved error handling"""
        try:
            page_source = self.load_page_source(url)
            if not page_source:
                return ScrapingResult("", [], False, "Failed to load page source")

            soup = BeautifulSoup(page_source, "lxml")
            new_urls = []

            # Extract links with improved filtering
            for link in soup.find_all("a", href=True):
                try:
                    new_url = urljoin(base_url, link["href"])
                    cleaned_url = self.remove_query_parameters(new_url)
                    if (
                        cleaned_url.startswith(base_url)
                        and not urlparse(cleaned_url).fragment
                        and self.is_valid_url(cleaned_url)
                    ):
                        new_urls.append(cleaned_url)
                except Exception as e:
                    GlobalLogger().error(f"Error processing link in {url}: {str(e)}")
                    continue

            # Extract text with improved cleaning
            texts = []
            for string in soup.stripped_strings:
                cleaned_text = " ".join(string.split())
                if cleaned_text:
                    texts.append(cleaned_text)

            page_text = " ".join(texts)
            return ScrapingResult(page_text, new_urls, True)

        except Exception as e:
            GlobalLogger().error(f"Error fetching URL: {url} - {str(e)}")
            return ScrapingResult("", [], False, str(e))


async def get_url_list_mapping(urls: List[str]) -> Dict[str, str]:
    """Process multiple URLs concurrently"""
    if not urls:
        return {}

    scraper = WebScraper()
    mappings = {}

    async def process_url(url: str) -> Tuple[str, Optional[str]]:
        result = scraper.fetch_url_content(url, url)
        return url, result.text if result.success else None

    tasks = [process_url(url) for url in urls]
    results = await asyncio.gather(*tasks)

    return {url: text for url, text in results if text is not None}


async def get_all_urls_mapping(base_url: str, max_depth: int = 5) -> Dict[str, str]:
    """Crawl website with improved handling of depth and limits"""
    scraper = WebScraper()
    resolved_url = scraper.resolve_redirects(base_url)

    visited_urls: Set[str] = set()
    urls_to_visit: List[Tuple[str, int]] = [(resolved_url, 1)]
    url_text_mapping: Dict[str, str] = {}

    async def process_url_batch(urls: List[str], depth: int) -> List[ScrapingResult]:
        return await asyncio.gather(
            *[
                asyncio.to_thread(scraper.fetch_url_content, url, base_url)
                for url in urls
            ]
        )

    try:
        while urls_to_visit and len(visited_urls) < MAX_URLS:
            current_batch = [
                (url, depth)
                for url, depth in urls_to_visit
                if depth <= max_depth and url not in visited_urls
            ][:MAX_THREADS]

            if not current_batch:
                break

            current_urls = [url for url, _ in current_batch]
            current_depths = [depth for _, depth in current_batch]

            visited_urls.update(current_urls)
            urls_to_visit = [
                item for item in urls_to_visit if item[0] not in visited_urls
            ]

            results = await process_url_batch(current_urls, max_depth)

            for url, depth, result in zip(current_urls, current_depths, results):
                if result.success and result.text:
                    url_text_mapping[url] = result.text
                    for new_url in result.urls:
                        if new_url not in visited_urls and new_url not in [
                            u for u, _ in urls_to_visit
                        ]:
                            urls_to_visit.append((new_url, depth + 1))

    except Exception as e:
        GlobalLogger().error(f"Error in crawling process: {str(e)}")

    return url_text_mapping


def url_mappings_to_storable_content(
    mapping: Dict[str, str]
) -> Tuple[List[Dict], List[Dict]]:
    """Convert URL mappings to storable content with validation"""
    content_list = []
    content_mapping_list = []

    for url, text in mapping.items():
        if not text.strip():
            continue

        content_id = str(uuid.uuid4())
        content_list.append(generateContentItem(content_id, text))
        content_mapping_list.append(
            generateContentMappingItem(content_id, url, URL, text)
        )

    return content_list, content_mapping_list


def get_filtered_content_mapping(
    uid: str, bot_id: str, mapping: Dict[str, str]
) -> List[Dict]:
    """Get filtered content mapping with duplicate handling"""
    current_collections = getContentMappingList(uid, bot_id)
    existing_urls = {
        item[SOURCE] for item in current_collections if item[SOURCE_TYPE] == URL
    }

    filtered_mapping = {
        key: value for key, value in mapping.items() if key not in existing_urls
    }

    if not filtered_mapping:
        return []

    content_list, content_mapping_list = url_mappings_to_storable_content(
        filtered_mapping
    )

    if content_list:
        storeContentList(content_list)
        current_collections.extend(content_mapping_list)
        insertContentListInBotCollection(uid, bot_id, current_collections)

    return content_mapping_list


def update_final_mappings(uid: str, bot_id: str, mapping: List[Dict]) -> None:
    """Update final mappings with cleanup"""
    current_mappings = getContentMappingList(uid, bot_id)
    removed_content_ids = [
        item[CONTENT_ID]
        for item in current_mappings
        if item[SOURCE_TYPE] == URL
        and not any(map_item[CONTENT_ID] == item[CONTENT_ID] for map_item in mapping)
    ]

    if removed_content_ids:
        deleteContentID(removed_content_ids)

    getChatBotsCollection().update_one(
        {USER_ID: uid, CHATBOT_ID: bot_id}, {"$set": {CONTENT_LIST: mapping}}
    )
