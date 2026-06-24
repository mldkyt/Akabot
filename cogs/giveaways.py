import dateparser
from discord import Cog, Bot, SlashCommandGroup, ApplicationContext, NotFound, default_permissions
from discord.ext.tasks import loop

from utils.docs import Docs, DocsCommand, DocsCommandParameter
from utils.giveaways import create_giveaway, get_ending_giveaways, roll_winners, mark_giveaway_ended, GiveawayEndedView, \
    GiveawayView, clear_expired_giveaways, get_giveaway_joins, get_giveaway_info_by_mid
from utils.message_appends import apply_appends


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

        await ctx.respond(apply_appends(ctx.user.id, "Giveaway created!"), ephemeral=True)

    @giveaway_grp.command()
    @default_permissions(manage_guild=True)
    async def stats(self, ctx: ApplicationContext, message_id: str):
        """Check the giveaway stats (joins)"""
        joins = get_giveaway_joins(message_id)
        if joins is None:
            await ctx.respond("Giveaway not found!", ephemeral=True)
            return

        await ctx.respond(f"There are currently {joins} joined people in this giveaway", ephemeral=True)

    @giveaway_grp.command()
    @default_permissions(manage_guild=True)
    async def close(self, ctx: ApplicationContext, message_id: str):
        """Close the giveaway ahead of time and roll winners"""
        giveaway = get_giveaway_info_by_mid(message_id)
        if giveaway is None:
            await ctx.respond("Giveaway not found!", ephemeral=True)
            return

        if giveaway[4]:
            await ctx.respond("Cannot close a closed giveaway, please reroll instead", ephemeral=True)
            return

        guild = self.bot.get_guild(int(giveaway[1]))
        if guild is None:
            return

        channel = guild.get_channel(int(giveaway[2]))
        if channel is None:
            return

        try:
            message = await channel.fetch_message(int(giveaway[3]))
        except NotFound:
            return

        winners = roll_winners(message)
        if len(winners) == 0:
            await message.reply("No one won :(")
        else:
            await message.reply(
                "The winners for this giveaway are " + ", ".join([f"<@{j}>" for j in winners]) + "!",
                view=GiveawayEndedView(giveaway[0]))
        mark_giveaway_ended(giveaway[0])

        await ctx.respond("Giveaway successfully closed", ephemeral=True)


    @loop(minutes=1)
    async def giveaways_handler(self):
        ending_giveaways = get_ending_giveaways()
        for i in ending_giveaways:
            # id, gid, cid, mid
            guild = self.bot.get_guild(int(i[1]))
            if guild is None:
                continue

            channel = guild.get_channel(int(i[2]))
            if channel is None:
                continue

            try:
                message = await channel.fetch_message(int(i[3]))
            except NotFound:
                continue

            winners = roll_winners(message)
            if len(winners) == 0:
                await message.reply("No one won :(")
            else:
                await message.reply(
                    "The winners for this giveaway are " + ", ".join([f"<@{j}>" for j in winners]) + "!",
                    view=GiveawayEndedView(i[0]))
            mark_giveaway_ended(i[0])

        clear_expired_giveaways()


def setup(bot: Bot):
    bot.add_cog(Giveaways(bot))
