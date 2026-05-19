import os
import random
from typing import Any

from aiohttp import ClientSession
from discord import Embed, ApplicationContext, Color, EmbedAuthor, EmbedFooter, Member, User, Interaction
from discord.ui import View, button, Button
from sqlalchemy import select, update, insert, Connection, Row

from database import engine, consent
from logger import nekona_logger
from utils.message_appends import apply_appends
from utils.server_settings import ServerSetting, setting_to_boolean, setting_simple_string_boolean, SettingType

FEDI_INSTANCE = os.getenv("FEDI_INSTANCE")

YURIBOT_ID = os.getenv("YURIBOT_ID")
YAOIBOT_ID = os.getenv("YAOIBOT_ID")

setting_allow_rp_commands = ServerSetting(
    name="Allow RP commands",
    setting_type=SettingType.NORMAL,
    description="Allow roleplay commands in this server.",
    normal_processor=setting_to_boolean,
    normal_response=setting_simple_string_boolean("Roleplay commands are now %s", "enabled", "disabled"),
    normal_view=setting_simple_string_boolean("Roleplay commands are %s", "enabled", "disabled"),
    default="true"
)

setting_disable_yaoi_command = ServerSetting(
    name="Disable yaoi command",
    setting_type=SettingType.NORMAL,
    description="Whether the yaoi command should be disabled",
    normal_processor=setting_to_boolean,
    normal_response=setting_simple_string_boolean("The yaoi command is now %s", "disabled", "enabled"),
    normal_view=setting_simple_string_boolean("The yaoi command is %s", "disabled", "enabled"),
    default="false"
)

setting_disable_yuri_command = ServerSetting(
    name="Disable yuri command",
    setting_type=SettingType.NORMAL,
    description="Whether the yuri command should be disabled",
    normal_processor=setting_to_boolean,
    normal_response=setting_simple_string_boolean("The yuri command is now %s", "disabled", "enabled"),
    normal_view=setting_simple_string_boolean("The yuri command is %s", "disabled", "enabled"),
    default="false"
)

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
    "shrug": "$user doesn't know...",
    "stare": "$user is staring...",
    "wave": "$user is waving...",
    "poke": "$user poked $target :3",
    "smile": "$user smiled...",
    "wink": "$user winked...",
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
        await ctx.respond(f"An error occurred fetching {category} gif. Sorry", ephemeral=True)
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


class ConsentView(View):
    def __init__(self, source: User, target: User):
        super().__init__(timeout=600, disable_on_timeout=True)
        self.source = source
        self.target = target

    @button(label="Set level 1")
    async def consent_1(self, button: Button, interaction: Interaction):
        if interaction.user is None:
            return
        if interaction.user.id == self.source.id:
            await interaction.respond("The consent level has to be selected by the other user.", ephemeral=True)
            return
        if interaction.user.id != self.target.id:
            await interaction.respond("This selection is not yours.", ephemeral=True)
            return
        await set_consent(self.source, self.target, 1)
        await interaction.respond(apply_appends(interaction.user.id, "Set consent level 1."), ephemeral=True)
        self.stop()
        self.disable_all_items()
        await interaction.message.edit(view=self)

    @button(label="Set level 2")
    async def consent_2(self, button: Button, interaction: Interaction):
        if interaction.user is None:
            return
        if interaction.user.id == self.source.id:
            await interaction.respond("The consent level has to be selected by the other user.", ephemeral=True)
            return
        if interaction.user.id != self.target.id:
            await interaction.respond("This selection is not yours.", ephemeral=True)
            return
        await set_consent(self.source, self.target, 2)
        await interaction.respond(apply_appends(interaction.user.id, "Set consent level 2."), ephemeral=True)
        self.stop()
        self.disable_all_items()
        await interaction.message.edit(view=self)

    @button(label="Set level 3")
    async def consent_3(self, button: Button, interaction: Interaction):
        if interaction.user is None:
            return
        if interaction.user.id == self.source.id:
            await interaction.respond("The consent level has to be selected by the other user.", ephemeral=True)
            return
        if interaction.user.id != self.target.id:
            await interaction.respond("This selection is not yours.", ephemeral=True)
            return
        await set_consent(self.source, self.target, 3)
        await interaction.respond(apply_appends(interaction.user.id, "Set consent level 3."), ephemeral=True)
        self.stop()
        self.disable_all_items()
        await interaction.message.edit(view=self)

    @button(label="Do not consent")
    async def no_consent(self, button: Button, interaction: Interaction):
        if interaction.user is None:
            return
        if interaction.user.id == self.source.id:
            await interaction.respond("The consent level has to be selected by the other user.", ephemeral=True)
            return
        if interaction.user.id != self.target.id:
            await interaction.respond("This selection is not yours.", ephemeral=True)
            return
        await set_consent(self.source, self.target, 0)
        await interaction.respond(apply_appends(interaction.user.id, "You did not consent"), ephemeral=True)
        self.stop()
        self.disable_all_items()
        await interaction.message.edit(view=self)


def _get_consent_data(c: Connection, user_1: Member | User, user_2: Member | User) -> Row[Any] | None:
    # First check if the user IDs could be flipped in order to get le data
    r1 = c.execute(select(consent.c.uid1, consent.c.uid2, consent.c.consentlevel).where(
        (consent.c.uid1 == str(user_1.id)) & (consent.c.uid2 == str(user_2.id)))).fetchone()
    r2 = c.execute(select(consent.c.uid1, consent.c.uid2, consent.c.consentlevel).where(
        (consent.c.uid1 == str(user_2.id)) & (consent.c.uid2 == str(user_1.id)))).fetchone()
    return r1 or r2


async def get_consent(user_1: Member | User, user_2: Member | User):
    """Get consent level between 2 people."""
    with engine.begin() as c:
        res = _get_consent_data(c, user_1, user_2)
        if res is None:
            return 0
        return res[2]


async def set_consent(user_1: Member | User, user_2: Member | User, consent_level: int):
    with engine.begin() as c:
        res = _get_consent_data(c, user_1, user_2)
        if res is not None:
            c.execute(
                update(consent)
                .where((consent.c.uid1 == res[0]) & (consent.c.uid2 == res[1]))
                .values(consentlevel=consent_level)
            )
        else:
            c.execute(
                insert(consent)
                .values(uid1=str(user_1.id), uid2=str(user_2.id), consentlevel=consent_level)
            )


async def ensure_consent(ctx: ApplicationContext, target: Member | None, required_consent: int) -> bool:
    if ctx.user is None or target is None:
        await ctx.respond("The user couldn't be determined therefore the verification failed.", ephemeral=True)
        return False
    consent_level = await get_consent(ctx.user, target) or 0
    if consent_level >= required_consent:
        return True
    await ctx.respond("Please get enough consent before you can use this command against that user", ephemeral=True)
    return False

yaoi_cache = YaoiCache()
yuri_cache = YuriCache()
