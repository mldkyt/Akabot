from discord import Bot, Forbidden
from sqlalchemy import select

from database import engine, statistic_channels
from logger import akabot_logger


async def update(bot: Bot):
    with engine.begin() as c:
        for guild in bot.guilds:
            configured = c.execute(
                select(statistic_channels.c.cid, statistic_channels.c.template)
                .where(statistic_channels.c.gid == str(guild.id))
                .order_by(statistic_channels.c.id)
            ).fetchall()
            for i in configured:
                channel = guild.get_channel(int(i[0]))

                templ = i[1].strip()
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
