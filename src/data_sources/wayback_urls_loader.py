import asyncio
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import aiohttp
from src.logger.logger import GlobalLogger
from src.scripts.scrapper import LazyBrowserPool
from typing import Dict
from concurrent.futures import ThreadPoolExecutor


from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By


async def get_all_wayback_urls_mapping(
    base_url: str, count_limit: int
) -> Dict[str, str]:
    """
    Parallel URL fetching with proper waits and logging
    """
    url_text_mapping = {}
    browser_pool = None

    try:
        browser_pool = LazyBrowserPool.get_instance()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://web.archive.org/cdx/search/cdx?url={base_url}/*&output=txt&fl=original&collapse=urlkey",
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    all_urls = (await response.text()).split("\n")
        except Exception as e:
            GlobalLogger().error(f"Wayback fetch error: {e}")
            return url_text_mapping

        base_path = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"
        pattern = re.compile(r"^[^?]*(\.html$|\.php$|/[^/.]*$)")
        filtered_urls = [
            url
            for url in all_urls[:100]
            if url and pattern.search(url) and url.startswith(base_path)
        ][:count_limit]

        def fetch_with_browser(url: str) -> tuple[str, str]:
            browser = None
            try:
                print(f"Starting fetch for {url}")
                browser = browser_pool.get()
                if not browser:
                    # print(f"No browser available for {url}")
                    return url, ""

                # Set shorter timeouts
                browser.set_page_load_timeout(10)
                browser.implicitly_wait(5)

                # Navigate to URL
                # print(f"Navigating to {url}")
                browser.get(url)

                # Wait for body with timeout
                try:
                    WebDriverWait(browser, 5).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )

                    # Get page source after JavaScript execution
                    page_source = browser.execute_script(
                        "return document.documentElement.outerHTML"
                    )

                    if page_source:
                        # print(f"Got content for {url}, length: {len(page_source)}")
                        soup = BeautifulSoup(page_source, "lxml")
                        text_content = " ".join(soup.stripped_strings)
                        if text_content:
                            # print(f"Extracted text for {url}, length: {len(text_content)}")
                            return url, text_content
                except Exception as e:
                    # print(f"Error waiting for body on {url}: {e}")
                    pass

                return url, ""

            except Exception as e:
                # print(f"Error in fetch_with_browser for {url}: {e}")
                return url, ""
            finally:
                if browser:
                    try:
                        browser_pool.release(browser)
                    except Exception as e:
                        # print(f"Error releasing browser: {e}")
                        pass

        # Process URLs with improved error handling
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=browser_pool.size) as executor:
            futures = []
            for url in filtered_urls:
                future = loop.run_in_executor(executor, fetch_with_browser, url)
                futures.append((url, future))

            # Process results as they complete
            for url, future in futures:
                try:
                    result_url, content = await future
                    if content:
                        # print(f"Adding content for {url} to mapping")
                        url_text_mapping[url] = content
                except Exception as e:
                    # print(f"Error processing future for {url}: {e}")
                    continue

    except Exception as e:
        # print(f"Main process error: {e}")
        pass
    finally:
        if browser_pool:
            try:
                browser_pool.shutdown()
            except:
                pass

    # print(f"Final mapping count: {len(url_text_mapping)}")
    return url_text_mapping


# API endpoint
async def fetch_wayback_urls_api(base_url: str, count_limit: int = 20):
    result = await get_all_wayback_urls_mapping(
        base_url=base_url, count_limit=min(count_limit, 30)
    )
    # print(f"API returning {len(result)} results")
    return result
