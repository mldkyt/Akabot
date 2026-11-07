from discord import (
    ApplicationContext,
    Bot,
    ChannelType,
    Cog,
    Embed,
    Member,
    Message,
    Reaction,
    SlashCommandGroup,
    User,
    default_permissions,
    guild_only,
)
from discord.ext import commands
from discord.ext.tasks import loop

from database import engine
from logger import akabot_logger
from utils.tickets import (
    TicketCreateView,
    TicketMessageView,
    archive_inactive_tickets,
    hide_archived_tickets,
    is_archived,
    log_ticket_event,
    ticket_archive_time,
    ticket_hide_time,
    update_last_activity,
)
from utils.timezones import get_now


class Tickets(Cog):
    def __init__(self, bot: Bot):
        super().__init__()
        self.bot = bot

    tickets_commands = SlashCommandGroup(
        name="tickets", description="Manage tickets"
    )

    @Cog.listener()
    async def on_ready(self):
        self.bot.add_view(TicketMessageView())
        self.bot.add_view(TicketCreateView())

        if not self.handle_hiding.is_running():
            self.handle_hiding.start()
        if not self.handle_auto_archive.is_running():
            self.handle_auto_archive.start()

    @Cog.listener()
    async def on_message(self, message: Message):
        try:
            if message.author.bot or message.guild is None:
                return

            if message.channel.type == ChannelType.private:
                return  # Do not try to update ticket information in DMs

            with engine.begin() as c:
                if not is_ticket_channel(
                    c, message.guild.id, message.channel.id
                ):
                    return

                if is_archived(c, message.guild.id, message.channel.id):
                    return

                update_last_activity(
                    c, message.guild.id, message.channel.id
                )
        except Exception:
            akabot_logger.exception("An error occured:")

    @Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
        try:
            if after.author.bot or after.guild is None:
                return

            with engine.begin() as c:
                if not is_ticket_channel(
                    c, after.guild.id, after.channel.id
                ):
                    return

                if is_archived(c, after.guild.id, after.channel.id):
                    return

                update_last_activity(
                    c, after.guild.id, after.channel.id
                )
        except Exception:
            akabot_logger.exception("An error occured:")

    @Cog.listener()
    async def on_reaction_add(
        self, reaction: Reaction, user: User | Member
    ):
        try:
            if user.bot:
                return

            if reaction.message.guild is None:
                return

            with engine.begin() as c:
                if not is_ticket_channel(
                    c,
                    reaction.message.guild.id,
                    reaction.message.channel.id,
                ):
                    return

                if is_archived(
                    c,
                    reaction.message.guild.id,
                    reaction.message.channel.id,
                ):
                    return

                update_last_activity(
                    c,
                    reaction.message.guild.id,
                    reaction.message.channel.id,
                )
        except Exception:
            akabot_logger.exception("An error occured:")

    @tickets_commands.command(
        name="set_hide_time",
        description="Set the time that the ticket will be available for the "
        "creator after it's archived.",
    )
    @default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    @guild_only()
    async def set_hide_time(self, ctx: ApplicationContext, hours: int):
        try:
            if ctx.guild is None:
                return

            with engine.begin() as c:
                ticket_hide_time.set(c, ctx.guild.id, str(hours))

            await ctx.respond("Ticket hide time set.", ephemeral=True)

            log_embed = Embed(
                title="Ticket Hide Time Set",
                description=(
                    f"Ticket hide time set by {ctx.user.mention} to "
                    f"{hours} hours"
                ),
            )
            log_embed.add_field(
                name="Ticket Hide Time", value=str(hours)
            )
            log_embed.add_field(
                name="Ticket Hide Time Time",
                value=get_now(ctx.guild.id).isoformat(),
            )

            await log_ticket_event(ctx.guild, log_embed)
        except Exception:
            akabot_logger.exception("An error occured:")
            await ctx.respond("An error occurred.", ephemeral=True)

    @tickets_commands.command(
        name="set_archive_time",
        description="Set the time that the ticket will be archived after no "
        "activity.",
    )
    @default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    @guild_only()
    async def set_auto_archive_time(
        self, ctx: ApplicationContext, hours: int
    ):
        try:
            if ctx.guild is None:
                return

            with engine.begin() as c:
                ticket_archive_time.set(c, ctx.guild.id, str(hours))

            await ctx.respond("Ticket archive time set.", ephemeral=True)

            log_embed = Embed(
                title="Ticket Archive Time Set",
                description=(
                    f"Ticket archive time set by {ctx.user.mention} to "
                    f"{hours} hours"
                ),
            )
            log_embed.add_field(
                name="Ticket Archive Time", value=str(hours)
            )
            log_embed.add_field(
                name="Ticket Archive Time Time",
                value=get_now(ctx.guild.id).isoformat(),
            )

            await log_ticket_event(ctx.guild, log_embed)
        except Exception:
            akabot_logger.exception("An error occured:")
            await ctx.respond("An error occurred.", ephemeral=True)

    @loop(seconds=60)
    async def handle_hiding(self):
        try:
            await hide_archived_tickets(self.bot)
        except Exception:
            akabot_logger.exception("An error occured:")

    @loop(seconds=60)
    async def handle_auto_archive(self):
        try:
            await archive_inactive_tickets(self.bot)
        except Exception:
            akabot_logger.exception("An error occured:")


def setup(bot: Bot):
    bot.add_cog(Tickets(bot))
