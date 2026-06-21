from discord import Bot, Member, Forbidden
from sqlalchemy import Connection

from database import engine
from logger import akabot_logger
from utils.server_settings import ServerSetting, SettingType, setting_to_voice_channel


def statistic_channel_add_processor(c: Connection, m: Member, v: str) -> tuple[bool, str]:
    params = v.split(';')
    if len(params) != 2:
        return False, "Invalid amount of parameters"

    ok, channel = setting_to_voice_channel(c, m, params[0].strip())
    if not ok:
        return False, channel

    return True, ";".join([channel, params[1].strip()])


def statistic_channel_add_response(c: Connection, m: Member, v: str) -> str:
    params = v.split(';')

    return f"Turned <#{params[0]}> into a statistic channel with template \"{params[1]}\""


def statistic_channel_remove_processor(c: Connection, m: Member, v: str) -> tuple[bool, str]:
    channels = setting_statistic_channels.get(c, m.guild.id)
    channel = [i for i in channels if channels.lower().startswith(v.lower())]
    if len(channel) == 0:
        return False, "Channel not found"

    return True, channel[0]


def statistic_channel_remove_response(c: Connection, m: Member, v: str) -> str:
    params = v.split(';')

    return f"The channel <#{params[0]}> is no longer a statistics channel"


def statistic_channel_list_view(c: Connection, m: Member, v: list[str]) -> str:
    result_str = []
    for i in v:
        params = i.split(";")

        result_str.append(f"<#{params[0]}")

    return "Statistic channels: " + ", ".join(result_str)


setting_statistic_channels = ServerSetting(
    name="Statistic Channels",
    description="Set up statistic channels. Templates have {members}, {bots}, {users}, {guild} and {owner} so far. You can suggest more in the support Discord server :)",
    setting_type=SettingType.LIST,
    list_add_processor=statistic_channel_add_processor,
    list_add_response=statistic_channel_add_response,
    list_remove_processor=statistic_channel_remove_processor,
    list_remove_response=statistic_channel_remove_response,
    list_view=statistic_channel_list_view
)


async def update(bot: Bot):
    with engine.begin() as c:
        for guild in bot.guilds:
            statistic_channels = setting_statistic_channels.get(c, guild.id)
            for i in statistic_channels:

                params = i.split(";")

                channel = guild.get_channel(int(params[0]))

                templ = params[1].strip()
                templ = templ.replace("{members}", str(guild.member_count))
                templ = templ.replace("{bots}", str(len([i for i in guild.members if i.bot])))
                templ = templ.replace("{users}", str(len([i for i in guild.members if not i.bot])))
                templ = templ.replace("{guild}", guild.name)
                templ = templ.replace("{owner}", guild.owner.name)

                try:
                    await channel.edit(name=templ)
                except Forbidden:
                    pass
                except Exception:
                    akabot_logger.exception("Error updating statistic channel in %s", guild.name)
