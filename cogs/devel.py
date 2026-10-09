import datetime
import os

from discord import ApplicationContext, Bot, Cog, SlashCommandGroup, TextChannel, guild_only, option
from sqlalchemy import delete, insert, select, update

from database import (
    chat_streaks,
    chat_summary_channels,
    chat_summary_members,
    engine,
    monthly_chat_summary_channels,
    monthly_chat_summary_members,
    yearly_chat_summary_channels,
    yearly_chat_summary_members,
)
from logger import akabot_logger
from utils.ads import get_ad
from utils.chat_streaks import handle_send_reply
from utils.chat_summary import summarize


class Devel(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    devel_group = SlashCommandGroup(
        name="devel", guild_ids=[int(os.getenv("DEVEL_GUILD_ID", "0"))]
    )

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
                select(
                    chat_streaks.c.start_date, chat_streaks.c.last_message_date
                ).where(
                    (chat_streaks.c.gid == str(ctx.guild.id))
                    & (chat_streaks.c.uid == str(ctx.user.id))
                )
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
                        message_count=0,
                        message_count_date=datetime.date.today(),
                    )
                )
            else:
                start_date = existing[0]
                last_message_date = existing[1]

            msg = (
                f"Old: start_date={start_date}, last_message_date={last_message_date}\n"
            )

            if mode == "zero":
                start_date = datetime.date.today() - datetime.timedelta(days=7)
                last_message_date = datetime.date.today()
            elif mode == "one":
                start_date = datetime.date.today() - datetime.timedelta(days=7)
                last_message_date = datetime.date.today() - datetime.timedelta(days=1)
            else:
                start_date = datetime.date.today() - datetime.timedelta(days=7)
                last_message_date = datetime.date.today() - datetime.timedelta(days=3)

            msg += (
                f"New: start_date={start_date}, last_message_date={last_message_date}\n"
            )

            c.execute(
                update(chat_streaks)
                .values(
                    start_date=start_date,
                    last_message_date=last_message_date,
                    message_count=0,
                    message_count_date=datetime.date.today(),
                )
                .where(
                    (chat_streaks.c.gid == str(ctx.guild.id))
                    & (chat_streaks.c.uid == str(ctx.user.id))
                )
            )

        await ctx.respond(msg, ephemeral=True)

    @devel_group.command()
    @guild_only()
    @option(name="members", description="Number of fake leaderboard entries", type=int, default=15)
    async def test_chat_summary(self, ctx: ApplicationContext, members: int = 15):
        """Seed fake data and post a chat summary in the current channel"""

        if not isinstance(ctx.channel, TextChannel):
            await ctx.respond("This command only works in a text channel", ephemeral=True)
            return

        members = max(1, members)
        member_ids = [str(m.id) for m in ctx.guild.members[:members]]
        if not member_ids:
            member_ids = [str(ctx.user.id)]

        member_ids = member_ids[:members]

        gid = str(ctx.guild.id)
        cid = str(ctx.channel.id)
        now = datetime.datetime.now(datetime.UTC)
        total = sum(range(1, len(member_ids) + 1))

        with engine.begin() as c:
            c.execute(
                delete(chat_summary_channels).where(
                    (chat_summary_channels.c.gid == gid)
                    & (chat_summary_channels.c.cid == cid)
                )
            )
            c.execute(
                delete(chat_summary_members).where(
                    (chat_summary_members.c.gid == gid)
                    & (chat_summary_members.c.cid == cid)
                )
            )
            c.execute(
                delete(monthly_chat_summary_channels).where(
                    (monthly_chat_summary_channels.c.gid == gid)
                    & (monthly_chat_summary_channels.c.cid == cid)
                )
            )
            c.execute(
                delete(monthly_chat_summary_members).where(
                    (monthly_chat_summary_members.c.gid == gid)
                    & (monthly_chat_summary_members.c.cid == cid)
                )
            )
            c.execute(
                delete(yearly_chat_summary_channels).where(
                    (yearly_chat_summary_channels.c.gid == gid)
                    & (yearly_chat_summary_channels.c.cid == cid)
                )
            )
            c.execute(
                delete(yearly_chat_summary_members).where(
                    (yearly_chat_summary_members.c.gid == gid)
                    & (yearly_chat_summary_members.c.cid == cid)
                )
            )

            for table in (
                chat_summary_channels,
                monthly_chat_summary_channels,
                yearly_chat_summary_channels,
            ):
                c.execute(
                    insert(table).values(
                        gid=gid,
                        cid=cid,
                        messages=total,
                        last_member=member_ids[0],
                    )
                )

            for idx, uid in enumerate(member_ids, start=1):
                messages = len(member_ids) - idx + 1
                c.execute(
                    insert(chat_summary_members).values(
                        gid=gid, cid=cid, uid=uid, messages=messages, last_message=now
                    )
                )
                c.execute(
                    insert(monthly_chat_summary_members).values(
                        gid=gid, cid=cid, uid=uid, messages=messages, last_message=now
                    )
                )
                c.execute(
                    insert(yearly_chat_summary_members).values(
                        gid=gid, cid=cid, uid=uid, messages=messages, last_message=now
                    )
                )

        await ctx.respond(
            f"Seeded {len(member_ids)} fake entries for <#{cid}> (total {total}) and posting the summary...",
            ephemeral=True,
        )

        with engine.begin() as c:
            await summarize(c, ctx.guild)

    @devel_group.command()
    @guild_only()
    async def test_reply(self, ctx: ApplicationContext):
        msg = await ctx.channel.send("Sample message")

        await handle_send_reply(msg, "This is a test reply")

        await ctx.respond("OK", ephemeral=True)


def setup(bot: Bot):
    if os.getenv("DEVEL", "0") != "1":
        return

    if len(os.getenv("DEVEL_GUILD_ID", "").strip()) == 0:
        akabot_logger.warning(
            "Devel mode is on, but commands were not loaded due to missing guild id."
        )
        return

    bot.add_cog(Devel(bot))
