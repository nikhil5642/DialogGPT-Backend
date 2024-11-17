import asyncio
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import aiohttp
from typing import Dict
import time
from src.logger.logger import GlobalLogger


async def fetch_url_content(session: aiohttp.ClientSession, url: str) -> str:
    """Fetch URL content using aiohttp"""
    try:
        async with session.get(
            url, timeout=aiohttp.ClientTimeout(total=20)
        ) as response:
            if response.status == 200:
                html_content = await response.text()
                soup = BeautifulSoup(html_content, "lxml")

                # Remove unwanted elements
                for element in soup(["script", "style", "iframe", "img"]):
                    element.decompose()

                # Extract text content
                text_content = " ".join(soup.stripped_strings)

                if text_content:
                    GlobalLogger().info(f"Successfully fetched content for {url}")
                    return text_content

    except Exception as e:
        GlobalLogger().error(f"Error fetching content for {url}: {str(e)}")

    return ""


async def get_all_wayback_urls_mapping(
    base_url: str, count_limit: int
) -> Dict[str, str]:
    """Fetch and process URLs using aiohttp and BeautifulSoup"""
    url_text_mapping = {}

    try:
        # Create session with custom headers and longer timeout
        timeout = aiohttp.ClientTimeout(total=30)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        async with aiohttp.ClientSession(headers=headers, timeout=timeout) as session:
            # Fetch URLs from Wayback
            try:
                response = await session.get(
                    "http://web.archive.org/cdx/search/cdx",
                    params={
                        "url": f"{base_url}/*",
                        "output": "txt",
                        "fl": "original",
                        "collapse": "urlkey",
                    },
                )

                if response.status == 200:
                    text_data = await response.text()
                    all_urls = [
                        line.strip() for line in text_data.split("\n") if line.strip()
                    ]
                    GlobalLogger().info(f"Found {len(all_urls)} URLs from Wayback")
                else:
                    raise Exception(f"Failed to fetch URLs: {response.status}")

            except Exception as e:
                GlobalLogger().error(f"Error fetching Wayback URLs: {str(e)}")
                return url_text_mapping

            # Filter URLs
            base_path = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"
            pattern = re.compile(r"^[^?]*(\.html$|\.php$|/[^/.]*$)")
            filtered_urls = []

            for url in all_urls:
                if len(filtered_urls) >= count_limit:
                    break
                try:
                    if url and pattern.search(url) and url.startswith(base_path):
                        filtered_urls.append(url)
                except Exception as e:
                    GlobalLogger().warning(f"Error filtering URL {url}: {str(e)}")

            GlobalLogger().info(f"Filtered to {len(filtered_urls)} URLs")

            if not filtered_urls:
                return url_text_mapping

            # Process URLs in parallel with rate limiting
            tasks = []
            semaphore = asyncio.Semaphore(5)  # Limit concurrent requests

            async def fetch_with_semaphore(url: str):
                async with semaphore:
                    content = await fetch_url_content(session, url)
                    if content:
                        url_text_mapping[url] = content
                    await asyncio.sleep(1)  # Rate limiting

            for url in filtered_urls:
                task = asyncio.create_task(fetch_with_semaphore(url))
                tasks.append(task)

            # Wait for all tasks to complete
            await asyncio.gather(*tasks)

    except Exception as e:
        GlobalLogger().error(f"Main process error: {str(e)}")

    GlobalLogger().info(
        f"Successfully processed {len(url_text_mapping)} URLs out of {len(filtered_urls)} filtered URLs"
    )
    return url_text_mapping


async def fetch_wayback_urls_api(base_url: str, count_limit: int = 20):
    """API endpoint"""
    result = await get_all_wayback_urls_mapping(
        base_url=base_url, count_limit=min(count_limit, 30)
    )
    return result
