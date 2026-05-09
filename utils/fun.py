import os
import random

from aiohttp import ClientSession

from logger import nekona_logger

FEDI_INSTANCE = os.getenv("FEDI_INSTANCE")

YURIBOT_ID = os.getenv("YURIBOT_ID")
YAOIBOT_ID = os.getenv("YAOIBOT_ID")


class YaoiCache:
    def __init__(self) -> None:
        pass

    latest_yaoibot_posts = []

    async def fetch_yaoibot_posts(self):
        if FEDI_INSTANCE is None or len(FEDI_INSTANCE.strip()) == 0:
            return

        if YAOIBOT_ID is None or len(YAOIBOT_ID.strip()) == 0:
            return

        async with ClientSession() as session:
            async with session.post(
                    f"https://{FEDI_INSTANCE}/api/users/notes",
                    json={"userId": YAOIBOT_ID, "limit": 100, "withFiles": True},
            ) as req:
                if not req.ok:
                    nekona_logger.warning(
                        "Failed to fetch yaoi :( Status %d %s",
                        req.status,
                        await req.text(),
                    )
                    return

                self.latest_yaoibot_posts = await req.json()

    async def get_yaoibot_post(self):
        if len(self.latest_yaoibot_posts) == 0:
            await self.fetch_yaoibot_posts()

        if len(self.latest_yaoibot_posts) == 0:
            return None

        random_post = random.choice(self.latest_yaoibot_posts)
        self.latest_yaoibot_posts = [
            i for i in self.latest_yaoibot_posts if i["id"] != random_post["id"]
        ]

        return random_post


class YuriCache:
    def __init__(self) -> None:
        pass

    latest_yuribot_posts = []

    async def fetch_yuribot_posts(self):
        if FEDI_INSTANCE is None or len(FEDI_INSTANCE.strip()) == 0:
            return

        if YURIBOT_ID is None or len(YURIBOT_ID.strip()) == 0:
            return

        async with ClientSession() as session:
            async with session.post(
                    f"https://{FEDI_INSTANCE}/api/users/notes",
                    json={"userId": YURIBOT_ID, "limit": 100, "withFiles": True},
            ) as req:
                if not req.ok:
                    nekona_logger.warning(
                        "Failed to fetch yuri :( Status %d %s",
                        req.status,
                        await req.text(),
                    )
                    return

                self.latest_yuribot_posts = await req.json()

    async def get_yuribot_post(self):
        if len(self.latest_yuribot_posts) == 0:
            await self.fetch_yuribot_posts()

        if len(self.latest_yuribot_posts) == 0:
            return None

        random_post = random.choice(self.latest_yuribot_posts)
        self.latest_yuribot_posts = [
            i for i in self.latest_yuribot_posts if i["id"] != random_post["id"]
        ]

        return random_post


yaoi_cache = YaoiCache()
yuri_cache = YuriCache()
