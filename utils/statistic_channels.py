from discord import Bot, Forbidden

from database import engine
from logger import akabot_logger
from utils.server_settings import ServerSetting, SettingType

setting_statistic_channels = ServerSetting(
    name="Statistic Channels",
    setting_type=SettingType.LIST,
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
                templ = templ.replace(
                    "{bots}", str(len([i for i in guild.members if i.bot]))
                )
                templ = templ.replace(
                    "{users}", str(len([i for i in guild.members if not i.bot]))
                )
                templ = templ.replace("{guild}", guild.name)
                templ = templ.replace("{owner}", guild.owner.name)

                try:
                    await channel.edit(name=templ)
                except Forbidden:
                    akabot_logger.warning(
                        f"Forbidden to update statistic channel {channel} in guild {guild.id}"
                    )
                except Exception as e:
                    akabot_logger.exception(f"Failed to update statistic channel {channel}: {e}")
