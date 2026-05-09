import os
import random

from aiohttp import ClientSession
from discord import Embed, ApplicationContext, Color, EmbedAuthor, EmbedFooter, Member

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


async def nb_api(category: str) -> dict | None:
    """Nekos.best API call"""
    async with ClientSession() as session:
        async with session.get(f"https://nekos.best/api/v2/{category}") as req:
            if not req.ok:
                return None

            req_json = await req.json()
            return req_json["results"][0]


NB_TITLES = {
    "lurk": "$user is lurking...",
    "sleep": "$user is sleepy...",
    "clap": "$user is clapping...",
    "shrug": "$user doesn't know...",
    "stare": "$user is staring...",
    "wave": "$user is waving...",
    "poke": "$user poked $target :3",
    "smile": "$user smiled...",
    "wink": "$user winked...",
    "sip": "$user sipped...",
    "blush": "$user blushed...",
    "smug": "$user smugged...",
    "tickle": "$user tickles $target!",
    "yeet": "$user yeeted $target!",
    "highfive": "$user gave a high five to $target!",
    "wag": "$user wags their tail :3",
    "bite": "$user bit $target!",
    "cuddle": "$user cuddles $target :3",
    "kick": "$user kicked $target",
    "carry": "$user carries $target",
    "hug": "$user hugged $target",
    "bonk": "$user bonked $target",
    "pat": "$user patted $target",
    "kiss": "$user kissed $target",
    "slap": "$target got slapped by $user",
    "lappillow": "$target is now $user's pillow :3",
    "handhold": "$user is handholding with $target"
}


async def nb_embed(ctx: ApplicationContext, category: str, target: Member | None = None) -> Embed | None:
    nb = await nb_api(category)
    if nb is None:
        await ctx.respond(f"An error occured fetching {category} gif. Sorry", ephemeral=True)
        return None

    author = None
    if "artist_name" in nb and "artist_href" in nb:
        author = EmbedAuthor(name=nb["artist_name"], url=nb["artist_href"])

    footer = EmbedFooter(text="Powered by Nekona")
    if "source_url" in nb:
        footer = EmbedFooter(text=f"Powered by Nekona | [Source]({nb['source_url']})")

    if category in NB_TITLES:
        title = NB_TITLES[category]

        if target is not None:
            title = title.replace("$target", target.display_name)

        title = title.replace("$user", ctx.user.display_name)
    else:
        title = f"{ctx.user.display_name} is {category}ing..."

    embed = Embed(
        title=title,
        image=nb["url"],
        author=author,
        footer=footer,
        color=Color.nitro_pink()
    )

    return embed

yaoi_cache = YaoiCache()
yuri_cache = YuriCache()
