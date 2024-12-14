import asyncio
from src.data_sources.urls_loader_requests import get_all_urls_mapping
from src.data_sources.wayback_urls_loader import fetch_wayback_urls_api

import datetime


async def main():
    results = await get_all_urls_mapping("https://crmexpertsonline.com", 100)
    print(results)


if __name__ == "__main__":
    uid = "G2pJbmdftsc0uj5ZH2IguWggh4z1"
    botID = "e0de187e-10d5-4f02-a0c8-dd25b922d557"
    # print(getChatBotsCollection().find_one({USER_ID: uid, CHATBOT_ID: botID})[CONTENT_LIST] or [])
    # print(getAwsSecretKey("FIREBASE_CONFIG"))
    asyncio.run(main())
