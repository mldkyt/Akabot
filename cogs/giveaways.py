import dateparser
from discord import Cog, Bot, SlashCommandGroup, ApplicationContext, NotFound, default_permissions
from discord.ext.tasks import loop

from logger import nekona_logger
from utils.docs import Docs
from utils.giveaways import create_giveaway, get_ending_giveaways, roll_winners, mark_giveaway_ended, GiveawayEndedView, \
    GiveawayView, clear_expired_giveaways


class Giveaways(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_ready(self):
        self.giveaways_handler.start()
        self.bot.add_view(GiveawayView())

    giveaway_grp = SlashCommandGroup(name="giveaways", description="Giveaway commands")

    @giveaway_grp.command()
    @default_permissions(manage_guild=True)
    async def create(self, ctx: ApplicationContext, item: str, winner_count: int, end: str):
        """Create a giveaway. The item WILL BE SHOWN in the message!"""
        end_date = dateparser.parse(end)
        if end_date is None:
            await ctx.respond("Invalid end date format", ephemeral=True)
            return

        message = await ctx.channel.send(f"**Giveaway**\n{item}", view=GiveawayView())
        create_giveaway(message, winner_count, end_date)

        await ctx.respond("Giveaway created!", ephemeral=True)

    @loop(minutes=1)
    async def giveaways_handler(self):
        ending_giveaways = get_ending_giveaways()
        nekona_logger.debug("[Giveaways] %d ending giveaways", len(ending_giveaways))
        for i in ending_giveaways:
            # id, gid, cid, mid
            guild = self.bot.get_guild(int(i[1]))
            if guild is None:
                nekona_logger.debug("[Giveaways] Skipping giveaway %d: guild is none", i[0])
                continue

            channel = guild.get_channel(int(i[2]))
            if channel is None:
                nekona_logger.debug("[Giveaways] Skipping giveaway %d: channel is none", i[0])
                continue

            try:
                message = await channel.fetch_message(int(i[3]))
            except NotFound:
                nekona_logger.debug("[Giveaways] Skipping giveaway %d: message not found", i[0])
                continue

            winners = roll_winners(message)
            if len(winners) == 0:
                await message.reply("No one won :(")
            else:
                await message.reply(
                    "The winners for this giveaway are " + ", ".join([f"<@{j}>" for j in winners]) + "!",
                    view=GiveawayEndedView(i[0]))
            mark_giveaway_ended(i[0])
            nekona_logger.debug("[Giveaways] Marked %d as ended", i[0])

        clear_expired_giveaways()


def setup(bot: Bot):
    bot.add_cog(Giveaways(bot))


def docs():
    return str(
        Docs(
            name="Giveaways",
            description="Host giveaways in your server"
        )
    )
