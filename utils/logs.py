from discord import (
    AuditLogAction,
    ChannelType,
    Color,
    Embed,
    Emoji,
    Guild,
    Sticker,
    TextChannel,
)
from sqlalchemy import Connection, select

from database import logging_channels
from utils.server_settings import (
    ServerSetting,
    SettingType,
)

logging_channel = ServerSetting(
    name="Logging channel",
    setting_type=SettingType.NORMAL,
)

logging_settings: list[tuple[str, str]] = [
    ("emoji_create", "emoji creates"),
    ("emoji_delete", "emoji deletes"),
    ("emoji_update", "emoji updates"),
    ("sticker_create", "sticker creates"),
    ("sticker_delete", "sticker deletes"),
    ("sticker_update", "sticker updates"),
    ("automod_create", "AutoMod rule create"),
    ("automod_update", "AutoMod rule update"),
    ("automod_delete", "AutoMod rule delete"),
    ("member_ban", "member bans"),
    ("member_unban", "member unbans"),
    ("channel_create", "channel creates"),
    ("channel_update", "channel updates"),
    ("channel_delete", "channel deletes"),
    ("guild_update", "guild updates"),
    ("role_create", "role creates"),
    ("role_update", "role updates"),
    ("role_delete", "role deletes"),
    ("invite_create", "invite creates"),
    ("invite_delete", "invite deletes"),
    ("member_join", "member joins"),
    ("member_leave", "member leaves"),
    ("member_update", "member updates"),
    ("voice_join", "voice joins"),
    ("voice_leave", "voice leaves"),
    ("voice_move", "voice moves"),
    ("voice_deafen", "voice server-deafens"),
    ("voice_mute", "voice server-mutes"),
    ("reaction_add", "reaction adds"),
    ("reaction_remove", "reaction removes"),
    ("reaction_clear_all", "all reaction clears"),
    ("reaction_clear_emoji", "single reaction clears"),
    ("event_create", "event creates"),
    ("event_update", "event updates"),
    ("event_delete", "event deletes"),
    ("thread_create", "thread creates"),
    ("thread_update", "thread updates"),
    ("thread_delete", "thread deletes"),
    ("automod_kick", "Automod Actions kick"),
    ("automod_ban", "Automod Actions ban"),
    ("automod_mute", "Automod Actions mute"),
    ("anti_raid", "Anti Raid"),
]

basic_logging_settings: list[tuple[str, str]] = [
    ("member_join", "member joins"),
    ("member_leave", "member leaves"),
    ("member_ban", "member bans"),
    ("member_unban", "member unbans"),
    ("channel_create", "channel creates"),
    ("channel_delete", "channel deletes"),
    ("role_create", "role creates"),
    ("role_delete", "role deletes"),
]


async def send_message_to_log_channel(
    c: Connection, guild: Guild, msg_type: str, message: str | Embed
):
    channel_data = c.execute(
        select(logging_channels.c.cid).where(
            (logging_channels.c.gid == str(guild.id))
            & (logging_channels.c.type == msg_type)
        )
    ).fetchall()

    for channel in channel_data:
        channel = guild.get_channel(int(channel[0]))
        if not isinstance(channel, TextChannel):
            return

        if isinstance(message, str):
            await channel.send(embed=Embed(description=message, color=Color.red()))
        else:
            await channel.send(embed=message)


def str_channel_type(channel_type: ChannelType) -> str:
    text = channel_type.name.replace("_", " ").capitalize()
    if "thread" not in text:
        text = text + " Channel"
    return text


def format_perm_name(name: str) -> str:
    return name.replace("_", " ").title()


def format_overwrite(val: bool | None) -> str:
    if val is None:
        return "Inherited"
    return "Allowed" if val else "Denied"


async def handle_sticker(
    c: Connection, guild: Guild, before: Sticker | None, after: Sticker | None
):
    if before is None and after is not None:
        triggering_user = None
        if guild.me.guild_permissions.view_audit_log:
            async for action in guild.audit_logs(
                action=AuditLogAction.sticker_create, limit=1
            ):
                triggering_user = action.user

        embed = Embed(title="Sticker Added", color=Color.green())
        embed.description = f'A sticker named "{after.name}" was added.'

        embed.add_field(
            name="Added by",
            value=triggering_user.mention if triggering_user else "Unknown",
            inline=False,
        )
        await send_message_to_log_channel(c, guild, "sticker_create", embed)

    if before is not None and after is None:
        triggering_user = None
        if guild.me.guild_permissions.view_audit_log:
            async for action in guild.audit_logs(
                action=AuditLogAction.sticker_delete, limit=1
            ):
                triggering_user = action.user

        embed = Embed(title="Sticker was removed", color=Color.red())
        embed.description = f'Sticker "{before.name}" was removed.'

        embed.add_field(
            name="Deleted by",
            value=triggering_user.mention if triggering_user else "Unknown",
            inline=False,
        )
        await send_message_to_log_channel(c, guild, "sticker_delete", embed)

    if before is not None and after is not None:
        triggering_user = None
        if guild.me.guild_permissions.view_audit_log:
            async for action in guild.audit_logs(
                action=AuditLogAction.sticker_update, limit=1
            ):
                triggering_user = action.user

        embed = Embed(title="Sticker edited", color=Color.blue())
        if before.name and after.name and before.name != after.name:
            embed.add_field(
                name="Name",
                value=f"{before.name} -> {after.name}",
            )

        if (
            before.description
            and after.description
            and before.description != after.description
        ):
            embed.add_field(
                name="Description",
                value=f"{before.description} -> {after.description}",
            )

        if len(embed.fields) > 0:
            embed.add_field(
                name="Edited by",
                value=triggering_user.mention if triggering_user else "Unknown",
                inline=False,
            )
        await send_message_to_log_channel(c, guild, "sticker_update", embed)


async def handle_emoji(
    c: Connection, guild: Guild, before: Emoji | None, after: Emoji | None
):
    if before is None and after is not None:
        triggering_user = None
        if guild.me.guild_permissions.view_audit_log:
            async for action in guild.audit_logs(
                action=AuditLogAction.emoji_create, limit=1
            ):
                triggering_user = action.user

        embed = Embed(title="Emoji added", color=Color.green())

        if after.animated:
            embed.description = (
                f'An animated emoji "{after.name}" was added into this server.'
            )
        else:
            embed.description = f'An emoji "{after.name}" was added into this server.'

        embed.add_field(
            name="Added by",
            value=triggering_user.mention if triggering_user else "Unknown",
            inline=False,
        )
        await send_message_to_log_channel(c, guild, "emoji_create", embed)

    if before is not None and after is None:
        triggering_user = None
        if guild.me.guild_permissions.view_audit_log:
            async for action in guild.audit_logs(
                action=AuditLogAction.emoji_delete, limit=1
            ):
                triggering_user = action.user

        embed = Embed(title="Emoji removed", color=Color.red())
        if before.animated:
            embed.description = (
                f'An animated emoji "{before.name}" was removed from this server.'
            )
        else:
            embed.description = (
                f'An emoji "{before.name}" was removed from this server.'
            )

        embed.add_field(
            name="Removed by",
            value=triggering_user.mention if triggering_user else "Unknown",
            inline=False,
        )
        await send_message_to_log_channel(c, guild, "emoji_delete", embed)

    if before is not None and after is not None:
        triggering_user = None
        if guild.me.guild_permissions.view_audit_log:
            async for action in guild.audit_logs(
                action=AuditLogAction.emoji_update, limit=1
            ):
                triggering_user = action.user

        embed = Embed(title="Emoji renamed", color=Color.blue())
        if before.name != after.name:
            embed.add_field(
                name="Name",
                value=f"{before.name} -> {after.name}",
            )

        if len(embed.fields) > 0:
            embed.add_field(
                name="Renamed by",
                value=triggering_user.mention if triggering_user else "Unknown",
                inline=False,
            )
            await send_message_to_log_channel(c, guild, "emoji_update", embed)
