import re

from discord import ChannelType, Guild, Role, TextChannel
from discord.abc import Messageable


def convert_role(guild: Guild, value: str, index: int = 0) -> Role | None:
    # mention
    a = re.match(r"^<@&(\d+)>$", value)
    if a is not None:
        value = a.group(1)

    # ID
    if value.isnumeric():
        return guild.get_role(int(value))

    # Try and find it by name startswith
    by_name = [i for i in guild.roles if i.name.startswith(value)]
    if index < len(by_name):
        return by_name[index]

    # Try and find it by name contains
    by_name = [i for i in guild.roles if value in i.name]
    if index < len(by_name):
        return by_name[index]

    return None


def convert_text_channel(
    guild: Guild, value: str, index: int = 0
) -> TextChannel | None:
    # mention
    a = re.match(r"^<#(\d+)>$", value)
    if a is not None:
        value = a.group(1)

    # ID
    if value.isnumeric():
        ch = [i for i in guild.text_channels if i.id == int(value)]
        if index < len(ch):
            return ch[index]

    # Try and find it by name startswith
    by_name = [i for i in guild.text_channels if i.name.startswith(value)]
    if index < len(by_name):
        return by_name[index]

    # Try and find it by name contains
    by_name = [i for i in guild.text_channels if value in i.name]
    if index < len(by_name):
        return by_name[index]

    return None
