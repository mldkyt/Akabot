from discord import (
    ApplicationContext,
    Bot,
    ButtonStyle,
    CategoryChannel,
    ChannelType,
    Cog,
    Embed,
    Interaction,
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
from discord.ui import Button, View

from database import engine
from logger import akabot_logger
from utils.tickets import (
    add_ticket,
    archive_inactive_tickets,
    archive_ticket,
    get_ticket_creator,
    hide_archived_tickets,
    is_archived,
    is_ticket_channel,
    log_ticket_event,
    remove_ticket,
    ticket_archive_time,
    ticket_category,
    ticket_hide_time,
    update_last_activity,
)
from utils.timezones import get_now


class TicketMessageView(View):
    """View for the message sent on top of every ticket."""

    def __init__(self):
        super().__init__(timeout=None)

        close_button = Button(
            style=ButtonStyle.danger,
            label="Close Ticket",
            custom_id="close_ticket",
        )
        close_button.callback = self.close_ticket
        self.add_item(close_button)

    async def close_ticket(self, interaction: Interaction):
        if interaction.guild is None or interaction.channel is None:
            await interaction.response.send_message(
                "This can only be used in a server.", ephemeral=True
            )
            return

        with engine.begin() as c:
            if not is_ticket_channel(
                c, interaction.guild.id, interaction.channel.id
            ):
                await interaction.response.send_message(
                    "This is not a ticket channel.", ephemeral=True
                )
                return

            hide_hours = int(
                ticket_hide_time.get(c, interaction.guild.id) or 0
            )
            creator_id = get_ticket_creator(
                c, interaction.guild.id, interaction.channel.id
            )

        member = (
            interaction.guild.get_member(creator_id)
            if creator_id is not None
            else None
        )

        if hide_hours > 0:
            if member is not None:
                await interaction.channel.set_permissions(
                    member,
                    view_channel=True,
                    read_messages=True,
                    send_messages=False,
                )
            with engine.begin() as c:
                archive_ticket(
                    c, interaction.guild.id, interaction.channel.id
                )
        else:
            if member is not None:
                await interaction.channel.set_permissions(
                    member,
                    view_channel=False,
                    read_messages=False,
                    send_messages=False,
                )
            with engine.begin() as c:
                remove_ticket(
                    c, interaction.guild.id, interaction.channel.id
                )

        await interaction.channel.send(
            "Ticket closed by " + interaction.user.mention
        )

        if interaction.message is not None:
            # Use a fresh view so disabling the button does not affect the
            # persistent view instance shared by other ticket messages.
            closed_view = TicketMessageView()
            closed_view.disable_all_items()
            await interaction.message.edit(view=closed_view)

        await interaction.response.send_message(
            "Ticket closed!", ephemeral=True
        )


class TicketCreateView(View):
    def __init__(self, button_label: str = "Create Ticket"):
        super().__init__(timeout=None)

        create_button = Button(
            style=ButtonStyle.primary,
            label=button_label,
            custom_id="create_ticket",
        )
        create_button.callback = self.create_ticket
        self.add_item(create_button)

    async def create_ticket(self, interaction: Interaction):
        if interaction.guild is None:
            await interaction.response.send_message(
                "This can only be used in a server.", ephemeral=True
            )
            return

        with engine.begin() as c:
            category_id = int(
                ticket_category.get(c, interaction.guild.id) or 0
            )

        category = interaction.guild.get_channel(category_id)
        if not isinstance(category, CategoryChannel):
            await interaction.response.send_message(
                "A ticket category has to be set in order to create a "
                "ticket. Please ping the admins of the server to fix this.",
                ephemeral=True,
            )
            return

        channel = await category.create_text_channel(
            f"ticket-{interaction.user.name}",
            topic=f"Ticket for {interaction.user.display_name}",
            reason="Ticket creation",
        )

        # Set overwrite for the creator of the ticket, so they can see the
        # channel and send messages
        await channel.set_permissions(
            interaction.user, read_messages=True, send_messages=True
        )

        # Send initial message
        await channel.send(
            "Ticket created by "
            + interaction.user.mention
            + "\n\nYou can use the buttons below to manage the ticket.",
            view=TicketMessageView(),
        )

        with engine.begin() as c:
            add_ticket(
                c,
                interaction.guild.id,
                channel.id,
                interaction.user.id,
            )

        await interaction.response.send_message(
            "Ticket created! " + channel.mention, ephemeral=True
        )

        log_embed = Embed(
            title="Ticket Created",
            description=(
                f"Ticket created by {interaction.user.mention} in "
                f"{channel.mention}"
            ),
        )
        log_embed.add_field(name="Ticket ID", value=str(channel.id))
        log_embed.add_field(
            name="Ticket Creator", value=interaction.user.mention
        )
        log_embed.add_field(name="Ticket Channel", value=channel.mention)
        log_embed.add_field(name="Ticket Category", value=category.name)
        log_embed.add_field(
            name="Ticket Creation Time",
            value=get_now(interaction.guild.id).isoformat(),
        )

        await log_ticket_event(interaction.guild, log_embed)


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
        name="send_message",
        description="Send a message that allows users to create a ticket",
    )
    @default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    @guild_only()
    async def send_message(
        self,
        ctx: ApplicationContext,
        message: str,
        button_label: str,
    ):
        try:
            if ctx.guild is None:
                return

            with engine.begin() as c:
                category_id = int(
                    ticket_category.get(c, ctx.guild.id) or 0
                )

            if category_id == 0:
                await ctx.respond(
                    "Set a ticket category first.", ephemeral=True
                )
                return

            if ctx.guild.get_channel(category_id) is None:
                await ctx.respond(
                    "The configured ticket category no longer exists.",
                    ephemeral=True,
                )
                return

            if (
                not ctx.guild.me.guild_permissions.manage_channels
                or not ctx.guild.me.guild_permissions.manage_roles
            ):
                await ctx.respond(
                    "The bot needs Manage Channels and Manage Roles "
                    "permissions.",
                    ephemeral=True,
                )
                return

            await ctx.channel.send(
                message, view=TicketCreateView(button_label)
            )
            await ctx.respond("Message sent.", ephemeral=True)

            log_embed = Embed(
                title="Ticket Message Sent",
                description=(
                    f"Ticket message sent by {ctx.user.mention} in "
                    f"{ctx.channel.mention}"
                ),
            )
            log_embed.add_field(name="Ticket Message", value=message)
            log_embed.add_field(
                name="Ticket Message Button Label", value=button_label
            )
            log_embed.add_field(
                name="Ticket Message Channel", value=ctx.channel.mention
            )
            log_embed.add_field(
                name="Ticket Message Time",
                value=get_now(ctx.guild.id).isoformat(),
            )

            await log_ticket_event(ctx.guild, log_embed)
        except Exception:
            akabot_logger.exception("An error occured:")
            await ctx.respond("An error occurred.", ephemeral=True)

    @tickets_commands.command(
        name="set_category",
        description="Set the category where tickets will be created. "
        "Permissions will be copied from this category.",
    )
    @default_permissions(manage_guild=True)
    @commands.has_permissions(manage_guild=True)
    @guild_only()
    async def set_category(
        self, ctx: ApplicationContext, category: CategoryChannel
    ):
        try:
            if ctx.guild is None:
                return

            with engine.begin() as c:
                ticket_category.set(c, ctx.guild.id, str(category.id))

            await ctx.respond("Ticket category set.", ephemeral=True)

            log_embed = Embed(
                title="Ticket Category Set",
                description=(
                    f"Ticket category set by {ctx.user.mention} to "
                    f"{category.name}"
                ),
            )
            log_embed.add_field(
                name="Ticket Category", value=category.name
            )
            log_embed.add_field(
                name="Ticket Category ID", value=str(category.id)
            )
            log_embed.add_field(
                name="Ticket Category Time",
                value=get_now(ctx.guild.id).isoformat(),
            )

            await log_ticket_event(ctx.guild, log_embed)
        except Exception:
            akabot_logger.exception("An error occured:")
            await ctx.respond("An error occurred.", ephemeral=True)

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
