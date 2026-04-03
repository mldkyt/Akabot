import datetime
import os

from discord import Bot, Cog, SlashCommandGroup, ApplicationContext, option, guild_only
from sqlalchemy import select, insert, update

from database import engine, chat_streaks
from logger import nekona_logger
from utils.ads import get_ad


class Devel(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    devel_group = SlashCommandGroup(name="devel", guild_ids=[int(os.getenv("DEVEL_GUILD_ID", "0"))])

    @devel_group.command()
    async def ad_test(self, ctx: ApplicationContext):
        await ctx.respond("Test", view=get_ad())

    @devel_group.command()
    @guild_only()
    @option(name="mode", choices=["zero", "one", "more"])
    async def set_chat_streaks(self, ctx: ApplicationContext, mode: str):
        """set chat streak to today, yesterday or more days behind for testing"""

        with engine.begin() as c:
            existing = c.execute(
                select(chat_streaks.c.start_date, chat_streaks.c.last_message_date)
                .where((chat_streaks.c.gid == str(ctx.guild.id)) & (chat_streaks.c.uid == str(ctx.user.id)))
            ).fetchone()

            if not existing:
                start_date = datetime.date.today() - datetime.timedelta(days=1)
                last_message_date = datetime.date.today()

                c.execute(
                    insert(chat_streaks).values(
                        gid=str(ctx.guild.id),
                        uid=str(ctx.user.id),
                        start_date=start_date,
                        last_message_date=last_message_date,
                    )
                )
            else:
                start_date = existing[0]
                last_message_date = existing[1]

            msg = f"Old: start_date={start_date}, last_message_date={last_message_date}\n"

            if mode == "zero":
                start_date = datetime.date.today() - datetime.timedelta(days=7)
                last_message_date = datetime.date.today()
            elif mode == "one":
                start_date = datetime.date.today() - datetime.timedelta(days=7)
                last_message_date = datetime.date.today() - datetime.timedelta(days=1)
            else:
                start_date = datetime.date.today() - datetime.timedelta(days=7)
                last_message_date = datetime.date.today() - datetime.timedelta(days=3)

            msg += f"New: start_date={start_date}, last_message_date={last_message_date}\n"

            c.execute(
                update(chat_streaks)
                .values(start_date=start_date, last_message_date=last_message_date)
                .where((chat_streaks.c.gid == str(ctx.guild.id)) & (chat_streaks.c.uid == str(ctx.user.id)))
            )

        await ctx.respond(msg, ephemeral=True)



def setup(bot: Bot):
    if os.getenv("DEVEL", "0") != "1":
        return

    if len(os.getenv("DEVEL_GUILD_ID", "").strip()) == 0:
        nekona_logger.warning("Devel mode is on, but commands were not loaded due to missing guild id.")
        return

    bot.add_cog(Devel(bot))
