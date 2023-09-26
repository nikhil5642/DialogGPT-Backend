from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import platform
from queue import Queue
from fake_useragent import UserAgent

class LazyBrowserPool:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = BrowserPool(MAX_BROWSERS)
        return cls._instance

class BrowserPool:
    def __init__(self, size):
        self.browsers = Queue()
        self.size = size
        self._initialize()

    def _initialize(self):
        for _ in range(self.size):
            browser = self._create_browser()
            self.browsers.put(browser)

    def _create_browser(self):
        ua = UserAgent()
        
        options = Options()
        options.add_argument("--window-size=1920x1080")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        options.add_argument("--headless=new")
        options.add_argument("--incognito")
        options.add_argument(f"user-agent={ua.random}")

        # Speed up loading by disabling images and unnecessary features
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-animations")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource problems.
      
        os_name = platform.system()
        if os_name == "Linux":
            options.binary_location = "/usr/bin/chromium-browser"
        elif os_name == "Darwin":
            options.binary_location = "/Applications/Chromium.app/Contents/MacOS/Chromium"
        else:
            raise Exception("Unsupported OS.")
        
        browser = webdriver.Chrome(options=options)
        browser.set_page_load_timeout(10)  # 10 seconds
        return browser

    def get(self):
        return self.browsers.get()

    def release(self, browser):
        self.browsers.put(browser)

    def shutdown(self):
        while not self.browsers.empty():
            browser = self.browsers.get()
            browser.quit()

# ... Rest of the functions ...

MAX_BROWSERS = 5
MAX_THREADS = 10  # Adjust based on system's capability
