import os
import random

from discord import ButtonStyle
from discord.ui import View, Button

DISCORD_ID = os.getenv("DISCORD_ID", "")


class InviteBotAd(View):
    def __init__(self):
        super().__init__()

        self.add_item(
            Button(label="Invite the bot today!", style=ButtonStyle.url,
                   url=f"https://discord.com/oauth2/authorize?client_id={DISCORD_ID}")
        )


class VoteBotAd(View):
    def __init__(self):
        super().__init__()

        self.add_item(
            Button(label="Vote for the bot!", style=ButtonStyle.url, url=f"https://top.gg/bot/{DISCORD_ID}/vote")
        )


def get_ad() -> View | None:
    if os.getenv("DISABLE_ADS", "0") == "1":
        return None

    if len(DISCORD_ID.strip()) == 0:
        return None

    candidates: list[View] = [
        InviteBotAd(),
        VoteBotAd()
    ]

    if random.randint(1, 100) > 80:
        return random.choice(candidates)

    return None
