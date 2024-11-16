import asyncio
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import aiohttp
from src.logger.logger import GlobalLogger
from src.scripts.scrapper import LazyBrowserPool
from typing import Dict
from concurrent.futures import ThreadPoolExecutor


async def get_all_wayback_urls_mapping(
    base_url: str, count_limit: int
) -> Dict[str, str]:
    """
    Parallel URL fetching that always returns available mappings
    """
    url_text_mapping = {}
    browser_pool = None

    try:
        browser_pool = LazyBrowserPool.get_instance()

        # Fetch wayback URLs with timeout
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://web.archive.org/cdx/search/cdx?url={base_url}/*&output=txt&fl=original&collapse=urlkey",
                    timeout=aiohttp.ClientTimeout(total=3),
                ) as response:
                    all_urls = (await response.text()).split("\n")
        except Exception as e:
            GlobalLogger().error(f"Wayback fetch error: {e}")
            return {}

        # Quick filtering
        base_path = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"
        pattern = re.compile(r"^[^?]*(\.html$|\.php$|/[^/.]*$)")
        filtered_urls = [
            url
            for url in all_urls[:100]
            if url and pattern.search(url) and url.startswith(base_path)
        ][:count_limit]

        if not filtered_urls:
            return {}

        def fetch_with_browser(url: str) -> tuple[str, str]:
            """Thread pool function that safely handles failures"""
            browser = None
            try:
                browser = browser_pool.get()
                if not browser:
                    return url, ""

                browser.set_page_load_timeout(5)
                browser.get(url)
                html = browser.page_source

                if html:
                    soup = BeautifulSoup(html, "lxml")
                    return url, " ".join(soup.stripped_strings)
                return url, ""

            except Exception as e:
                GlobalLogger().error(f"Error fetching {url}: {e}")
                return url, ""
            finally:
                if browser:
                    try:
                        browser_pool.release(browser)
                    except:
                        pass

        # Process URLs in smaller batches
        BATCH_SIZE = browser_pool.size * 2  # Process in batches of twice the pool size
        loop = asyncio.get_event_loop()

        async def process_batch(urls: list) -> Dict[str, str]:
            batch_results = {}
            with ThreadPoolExecutor(max_workers=browser_pool.size) as executor:
                futures = [
                    loop.run_in_executor(executor, fetch_with_browser, url)
                    for url in urls
                ]

                # Wait for batch with timeout
                try:
                    completed, pending = await asyncio.wait(
                        futures, timeout=10, return_when=asyncio.ALL_COMPLETED
                    )

                    # Process completed results
                    for future in completed:
                        try:
                            url, content = await future
                            if content:
                                batch_results[url] = content
                        except Exception as e:
                            GlobalLogger().error(f"Error processing result: {e}")
                            continue

                    # Cancel pending
                    for future in pending:
                        future.cancel()

                except Exception as e:
                    GlobalLogger().error(f"Batch processing error: {e}")

                return batch_results

        # Process all URLs in batches
        for i in range(0, len(filtered_urls), BATCH_SIZE):
            batch = filtered_urls[i : i + BATCH_SIZE]
            batch_results = await process_batch(batch)
            url_text_mapping.update(batch_results)

    except Exception as e:
        GlobalLogger().error(f"Error in main process: {e}")
    finally:
        if browser_pool:
            try:
                browser_pool.shutdown()
            except:
                pass

    return url_text_mapping


# API endpoint
async def fetch_wayback_urls_api(base_url: str, count_limit: int = 20):
    try:
        result = await get_all_wayback_urls_mapping(
            base_url=base_url, count_limit=min(count_limit, 30)
        )
        return {"status": "success", "data": result}
    except Exception as e:
        GlobalLogger().error(f"API error: {e}")
        return {
            "status": "success",
            "data": {},
        }  # Always return success with available data
