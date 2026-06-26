import datetime

from discord import (
    ApplicationContext,
    Bot,
    Cog,
    Guild,
    Member,
    Message,
    SlashCommandGroup,
    TextChannel,
    Thread,
    VoiceChannel,
    guild_only,
    option,
    slash_command,
)

from database import engine
from utils.moderation_commands import (
    is_user_moderator,
    perform_basic_checks,
)


class ModerationCommands(Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    @guild_only()
    @option(
        name="user",
        description="Member to kick from the server",
        type=Member,
        required=True,
    )
    @option(
        name="reason",
        description="Reason to write into the server log and audit log",
        type=str,
    )
    @slash_command()
    async def kick(self, ctx: ApplicationContext, user: Member, reason: str = ""):
        """Kick a member from the server"""
        if not isinstance(ctx.user, Member):
            await ctx.respond("This command must be run in a guild", ephemeral=True)
            return

        if not isinstance(ctx.guild, Guild):
            return

        with engine.begin() as c:
            ok, err = await perform_basic_checks(c, ctx, user, "kick")
            if not ok:
                await ctx.respond(err, ephemeral=True)
                return

            # Check permissions of bot
            if not ctx.guild.me.guild_permissions.kick_members:
                await ctx.respond(
                    "No kick permission on either bot or user", ephemeral=True
                )
                return

            try:
                await ctx.guild.kick(user, reason=reason)
                if reason.strip() == "":
                    await ctx.respond(f"User {user.mention} was kicked", ephemeral=True)
                else:
                    await ctx.respond(
                        f"User {user.mention} was kicked for {reason}", ephemeral=True
                    )
            except Exception:
                await ctx.respond("Error kicking the user", ephemeral=True)

    @guild_only()
    @option(
        name="user",
        description="Member to ban from the server",
        type=Member,
        required=True,
    )
    @option(
        name="reason",
        description="Reason to write into the server log and audit log",
        type=str,
    )
    @slash_command()
    async def ban(self, ctx: ApplicationContext, user: Member, reason: str = ""):
        """Ban a user from the server"""
        if not isinstance(ctx.user, Member):
            await ctx.respond("This command must be run in a guild", ephemeral=True)
            return

        if not isinstance(ctx.guild, Guild):
            return

        with engine.begin() as c:
            ok, err = await perform_basic_checks(c, ctx, user, "ban")
            if not ok:
                await ctx.respond(err, ephemeral=True)
                return

            # Check permissions of bot
            if not ctx.guild.me.guild_permissions.ban_members:
                await ctx.respond(
                    "No ban permission on either bot or user", ephemeral=True
                )
                return

            try:
                await ctx.guild.ban(user, reason=reason)
                if reason.strip() == "":
                    await ctx.respond(f"User {user.mention} was banned", ephemeral=True)
                else:
                    await ctx.respond(
                        f"User {user.mention} was banned for {reason}", ephemeral=True
                    )
            except Exception:
                await ctx.respond("Error banning the user", ephemeral=True)

    @guild_only()
    @option(
        name="user",
        description="Member to time out",
        type=Member,
        required=True,
    )
    @option(
        name="reason",
        description="Reason to write into the server log and audit log",
        type=str,
    )
    @option(
        name="days",
        type=int,
        description="Days of timeout; will be added up with other parameters",
        required=True,
    )
    @option(
        name="hours",
        type=int,
        description="Hours of timeout; will be added up with other parameters",
    )
    @option(
        name="minutes",
        type=int,
        description="Minutes of timeout; will be added up with other parameters",
    )
    @slash_command()
    async def timeout(
        self,
        ctx: ApplicationContext,
        user: Member,
        days: int,
        hours: int = 0,
        minutes: int = 0,
        reason: str = "",
    ):
        """Mute a user on the server"""
        if not isinstance(ctx.user, Member):
            return
        if not isinstance(ctx.guild, Guild):
            return

        timedelta = datetime.timedelta(days=days, hours=hours, minutes=minutes)
        if datetime.datetime.now() > datetime.datetime.now() + timedelta:
            await ctx.respond("The time must not be in the past", ephemeral=True)
            return

        if timedelta > datetime.timedelta(days=28):
            await ctx.respond("Max timeout time is 28 days", ephemeral=True)
            return

        with engine.begin() as c:
            ok, err = await perform_basic_checks(c, ctx, user, "mute")
            if not ok:
                await ctx.respond(err, ephemeral=True)
                return

            # Check permissions of bot
            if not ctx.guild.me.guild_permissions.mute_members:
                await ctx.respond(
                    "No mute permission on either bot or user", ephemeral=True
                )
                return

            try:
                await user.timeout_for(timedelta, reason=reason)
                if reason.strip() == "":
                    await ctx.respond(
                        f"User {user.mention} was timed out", ephemeral=True
                    )
                else:
                    await ctx.respond(
                        f"User {user.mention} was timed out for {reason}",
                        ephemeral=True,
                    )
            except Exception:
                await ctx.respond("Error muting the user", ephemeral=True)

    @guild_only()
    @option(
        name="user",
        description="Member to unmute",
        type=Member,
        required=True,
    )
    @option(
        name="reason",
        description="Reason to write into the server log and audit log",
        type=str,
    )
    @slash_command()
    async def remove_timeout(
        self,
        ctx: ApplicationContext,
        user: Member,
        reason: str = "",
    ):
        """Unmute a user on the server"""
        if not isinstance(ctx.user, Member):
            return
        if not isinstance(ctx.guild, Guild):
            return

        with engine.begin() as c:
            ok, err = await perform_basic_checks(c, ctx, user, "unmute")
            if not ok:
                await ctx.respond(err, ephemeral=True)
                return

            # Check permissions of bot
            if not ctx.guild.me.guild_permissions.mute_members:
                await ctx.respond(
                    "No mute permission on either bot or user", ephemeral=True
                )
                return

            if not user.timed_out:
                await ctx.respond("Target is not timed out", ephemeral=True)
                return

            try:
                await user.remove_timeout(reason=reason)
                if reason.strip() == "":
                    await ctx.respond(
                        f"User {user.mention}'s timeout was removed",
                        ephemeral=True,
                    )
                else:
                    await ctx.respond(
                        f"User {user.mention}'s timeout was removed for {reason}",
                        ephemeral=True,
                    )
            except Exception:
                await ctx.respond("Error muting the user", ephemeral=True)

    purge_commands = SlashCommandGroup(name="purge", description="Purge commands")

    @guild_only()
    @option(
        name="count",
        description="Amount of messages to search for",
        type=int,
        min=1,
        max=100,
        required=True,
    )
    @option(
        name="author",
        description="Only delete messages by this user",
        type=Member,
        required=True,
    )
    @purge_commands.command(name="by")
    async def purge_by(self, ctx: ApplicationContext, count: int, author: Member):
        """Mass delete messages by the specified author"""
        if not isinstance(ctx.user, Member):
            await ctx.respond("Command is only allowed in guilds", ephemeral=True)
            return
        if not isinstance(ctx.guild, Guild):
            await ctx.respond("Command is only allowed in guilds", ephemeral=True)
            return
        if (
            not isinstance(ctx.channel, TextChannel)
            and not isinstance(ctx.channel, VoiceChannel)
            and not isinstance(ctx.channel, Thread)
        ):
            await ctx.respond("Invalid channel", ephemeral=True)
            return

        if (
            not ctx.guild.me.guild_permissions.manage_messages
            or not ctx.channel.permissions_for(ctx.guild.me).manage_messages
        ):
            await ctx.respond("The bot is missing permissions: Manage Messages")
            return

        if count < 1:
            await ctx.respond("Count must be more than 1", ephemeral=True)
            return

        if count > 100:
            await ctx.respond("Count must be less than 100", ephemeral=True)
            return

        with engine.begin() as c:
            if not is_user_moderator(c, ctx.user):
                await ctx.respond(
                    "You must be moderator to purge commands", ephemeral=True
                )
                return

            messages_to_delete: list[Message] = []

            async for message in ctx.channel.history(limit=count):
                if (
                    datetime.datetime.now(datetime.UTC) - message.created_at
                ).total_seconds() >= 1.2096e6:
                    continue

                if message.author != author:
                    continue

                messages_to_delete.append(message)

            await ctx.channel.delete_messages(messages_to_delete)
            await ctx.respond(
                f"Deleted {len(messages_to_delete)} messages.", ephemeral=True
            )

    @guild_only()
    @option(
        name="count",
        description="Amount of messages to search for",
        type=int,
        min=1,
        max=100,
        required=True,
    )
    @purge_commands.command(name="media")
    async def purge_media(self, ctx: ApplicationContext, count: int):
        """Mass delete media in the current channel"""
        if not isinstance(ctx.user, Member):
            await ctx.respond("Command is only allowed in guilds", ephemeral=True)
            return
        if not isinstance(ctx.guild, Guild):
            await ctx.respond("Command is only allowed in guilds", ephemeral=True)
            return
        if (
            not isinstance(ctx.channel, TextChannel)
            and not isinstance(ctx.channel, VoiceChannel)
            and not isinstance(ctx.channel, Thread)
        ):
            await ctx.respond("Invalid channel", ephemeral=True)
            return

        if (
            not ctx.guild.me.guild_permissions.manage_messages
            or not ctx.channel.permissions_for(ctx.guild.me).manage_messages
        ):
            await ctx.respond("The bot is missing permissions: Manage Messages")
            return

        if count < 1:
            await ctx.respond("Count must be more than 1", ephemeral=True)
            return

        if count > 100:
            await ctx.respond("Count must be less than 100", ephemeral=True)
            return

        with engine.begin() as c:
            if not is_user_moderator(c, ctx.user):
                await ctx.respond(
                    "You must be moderator to purge commands", ephemeral=True
                )
                return

            messages_to_delete: list[Message] = []

            async for message in ctx.channel.history(limit=count):
                if (
                    datetime.datetime.now(datetime.UTC) - message.created_at
                ).total_seconds() >= 1.2096e6:
                    continue

                if len(message.attachments) == 0:
                    continue

                messages_to_delete.append(message)

            await ctx.channel.delete_messages(messages_to_delete)
            await ctx.respond(
                f"Deleted {len(messages_to_delete)} messages.", ephemeral=True
            )

    @guild_only()
    @option(
        name="count",
        description="Amount of messages to search for",
        type=int,
        min=1,
        max=100,
        required=True,
    )
    @option(
        name="author",
        description="Only delete messages by this user",
        type=Member,
        required=True,
    )
    @purge_commands.command(name="media_by")
    async def purge_media_by(self, ctx: ApplicationContext, count: int, author: Member):
        """Mass delete media by an author in this channel"""
        if not isinstance(ctx.user, Member):
            await ctx.respond("Command is only allowed in guilds", ephemeral=True)
            return
        if not isinstance(ctx.guild, Guild):
            await ctx.respond("Command is only allowed in guilds", ephemeral=True)
            return
        if (
            not isinstance(ctx.channel, TextChannel)
            and not isinstance(ctx.channel, VoiceChannel)
            and not isinstance(ctx.channel, Thread)
        ):
            await ctx.respond("Invalid channel", ephemeral=True)
            return

        if (
            not ctx.guild.me.guild_permissions.manage_messages
            or not ctx.channel.permissions_for(ctx.guild.me).manage_messages
        ):
            await ctx.respond("The bot is missing permissions: Manage Messages")
            return

        if count < 1:
            await ctx.respond("Count must be more than 1", ephemeral=True)
            return

        if count > 100:
            await ctx.respond("Count must be less than 100", ephemeral=True)
            return

        with engine.begin() as c:
            if not is_user_moderator(c, ctx.user):
                await ctx.respond(
                    "You must be moderator to purge commands", ephemeral=True
                )
                return

            messages_to_delete: list[Message] = []

            async for message in ctx.channel.history(limit=count):
                if (
                    datetime.datetime.now(datetime.UTC) - message.created_at
                ).total_seconds() >= 1.2096e6:
                    continue

                if message.author != author:
                    continue

                if len(message.attachments) == 0:
                    continue

                messages_to_delete.append(message)

            await ctx.channel.delete_messages(messages_to_delete)
            await ctx.respond(
                f"Deleted {len(messages_to_delete)} messages.", ephemeral=True
            )

    @guild_only()
    @option(
        name="count",
        description="Amount of messages to search for",
        type=int,
        min=1,
        max=100,
        required=True,
    )
    @purge_commands.command(name="all")
    async def purge_all(self, ctx: ApplicationContext, count: int):
        """Delete message in the current channel"""
        if not isinstance(ctx.user, Member):
            await ctx.respond("Command is only allowed in guilds", ephemeral=True)
            return
        if not isinstance(ctx.guild, Guild):
            await ctx.respond("Command is only allowed in guilds", ephemeral=True)
            return
        if (
            not isinstance(ctx.channel, TextChannel)
            and not isinstance(ctx.channel, VoiceChannel)
            and not isinstance(ctx.channel, Thread)
        ):
            await ctx.respond("Invalid channel", ephemeral=True)
            return

        if (
            not ctx.guild.me.guild_permissions.manage_messages
            or not ctx.channel.permissions_for(ctx.guild.me).manage_messages
        ):
            await ctx.respond("The bot is missing permissions: Manage Messages")
            return

        if count < 1:
            await ctx.respond("Count must be more than 1", ephemeral=True)
            return

        if count > 100:
            await ctx.respond("Count must be less than 100", ephemeral=True)
            return

        with engine.begin() as c:
            if not is_user_moderator(c, ctx.user):
                await ctx.respond(
                    "You must be moderator to purge commands", ephemeral=True
                )
                return

            messages_to_delete: list[Message] = []

            async for message in ctx.channel.history(limit=count):
                if (
                    datetime.datetime.now(datetime.UTC) - message.created_at
                ).total_seconds() >= 1.2096e6:
                    continue

                messages_to_delete.append(message)

            await ctx.channel.delete_messages(messages_to_delete)
            await ctx.respond(
                f"Deleted {len(messages_to_delete)} messages.", ephemeral=True
            )


def setup(bot: Bot):
    bot.add_cog(ModerationCommands(bot))
