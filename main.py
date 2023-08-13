import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

def get_all_urls_and_text(base_url, max_depth=10):
    visited_urls = set()
    urls_to_visit = [(base_url, 1)]  # Tuple with URL and depth
    url_text_mapping = {}  # Store URL and its associated text content

    while urls_to_visit:
        url, depth = urls_to_visit.pop(0)
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
                    if urlparse(new_url).netloc == urlparse(base_url).netloc:
                        urls_to_visit.append((new_url, depth + 1))

                # Store the text content associated with the current URL
                page_text = ' '.join(soup.stripped_strings)
                url_text_mapping[url] = page_text

        except Exception as e:
            print(f"Error fetching URL: {url}")
            print(e)

    return url_text_mapping

if __name__ == "__main__":
    website_url = "https://dreamkidsdeals.com"  # Replace with the website URL you want to scrape
    max_depth = 5  # Set the maximum depth to crawl

    url_text_mapping = get_all_urls_and_text(website_url, max_depth=max_depth)

    file_path = 'my_file.txt'
    with open(file_path, 'w') as file:
        for url, text in url_text_mapping.items():
            print(url,"   ",len(text))
            file.write(f"URL: {url}")
            file.write(f"Text:\n{text}")  # Print the first 500 characters of text
            file.write("\n")
