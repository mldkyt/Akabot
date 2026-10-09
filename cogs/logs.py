from discord import (
    AuditLogAction,
    AutoModRule,
    Bot,
    Cog,
    Color,
    ContentFilter,
    Embed,
    Emoji,
    Guild,
    Invite,
    Member,
    Message,
    NotificationLevel,
    NSFWLevel,
    Reaction,
    Role,
    ScheduledEvent,
    Sticker,
    Thread,
    User,
    VerificationLevel,
    VoiceState,
)
from discord.abc import GuildChannel

from database import engine
from logger import akabot_logger
from utils.logs import (
    format_overwrite,
    format_perm_name,
    handle_emoji,
    handle_sticker,
    send_message_to_log_channel,
)


class Logging(Cog):
    def __init__(self, bot: Bot) -> None:
        super().__init__()
        self.bot = bot

    @Cog.listener()
    async def on_guild_emojis_update(
        self, guild: Guild, before: tuple[Emoji], after: tuple[Emoji]
    ):
        with engine.begin() as c:
            try:
                if len(before) > len(after):  # Sticker deleted
                    for i in before:
                        if i not in after:
                            await handle_emoji(c, guild, i, None)

                elif len(after) > len(before):  # Sticker created
                    for i in after:
                        if i not in before:
                            await handle_emoji(c, guild, None, i)

                else:
                    for b, a in zip(before, after):
                        if b.name == a.name:
                            continue

                        await handle_emoji(c, guild, b, a)

            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_guild_stickers_update(
        self, guild: Guild, before: tuple[Sticker], after: tuple[Sticker]
    ):
        with engine.begin() as c:
            try:
                if len(before) > len(after):  # Sticker deleted
                    for i in before:
                        if i not in after:
                            await handle_sticker(c, guild, i, None)

                elif len(after) > len(before):  # Sticker created
                    for i in after:
                        if i not in before:
                            await handle_sticker(c, guild, None, i)

                else:
                    for b, a in zip(before, after):
                        if b.name == a.name:
                            continue

                        await handle_sticker(c, guild, b, a)

            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_auto_moderation_rule_create(self, rule: AutoModRule):
        if rule.guild is None:
            return

        with engine.begin() as c:
            try:
                moderator = None
                if rule.guild.me.guild_permissions.view_audit_log:
                    async for entry in rule.guild.audit_logs(
                        limit=1, action=AuditLogAction.auto_moderation_rule_create
                    ):
                        moderator = entry.user

                embed = Embed(
                    title="AutoMod rule was created",
                    color=Color.green(),
                )
                embed.add_field(name="Rule name", value=rule.name)
                embed.add_field(
                    name="Created by",
                    value=moderator.mention if moderator else "Unknown",
                )
                await send_message_to_log_channel(
                    c, rule.guild, "automod_create", embed
                )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_auto_moderation_rule_delete(self, rule: AutoModRule):
        if rule.guild is None:
            return

        with engine.begin() as c:
            try:
                moderator = None
                if rule.guild.me.guild_permissions.view_audit_log:
                    async for entry in rule.guild.audit_logs(
                        limit=1, action=AuditLogAction.auto_moderation_rule_delete
                    ):
                        moderator = entry.user
                embed = Embed(
                    title="AutoMod rule deleted",
                    color=Color.red(),
                )
                embed.add_field(name="Rule name", value=rule.name)
                embed.add_field(
                    name="Deleted by",
                    value=moderator.mention if moderator else "Unknown",
                )
                await send_message_to_log_channel(
                    c, rule.guild, "automod_delete", embed
                )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_auto_moderation_rule_update(self, rule: AutoModRule):
        if rule.guild is None:
            return

        with engine.begin() as c:
            try:
                moderator = None
                if rule.guild.me.guild_permissions.view_audit_log:
                    async for entry in rule.guild.audit_logs(
                        limit=1, action=AuditLogAction.auto_moderation_rule_update
                    ):
                        moderator = entry.user
                embed = Embed(
                    title="AutoMod rule edited",
                    color=Color.blue(),
                )
                embed.add_field(name="Rule name", value=rule.name)
                embed.add_field(
                    name="Edited by",
                    value=moderator.mention if moderator else "Unkown",
                )
                await send_message_to_log_channel(
                    c, rule.guild, "automod_update", embed
                )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_member_ban(self, guild: Guild, user: User):
        with engine.begin() as c:
            try:
                reason = None
                moderator = None

                if guild.me.guild_permissions.view_audit_log:
                    async for entry in guild.audit_logs(
                        limit=1, action=AuditLogAction.ban
                    ):
                        if entry.target.id == user.id:
                            moderator = entry.user
                            reason = entry.reason
                            break

                embed = Embed(title="Member Banned", color=Color.red())
                embed.add_field(
                    name="Banned User",
                    value=f"{user.display_name} ({user.name}; {user.id})",
                )

                embed.add_field(
                    name="Banned by",
                    value=moderator.mention if moderator else "Unknown",
                )
                embed.add_field(
                    name="Reason of ban",
                    value=reason if reason else "*Not specified*",
                )
                await send_message_to_log_channel(c, guild, "member_ban", embed)
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_member_unban(self, guild: Guild, user: User):
        with engine.begin() as c:
            try:
                reason = None
                moderator = None

                if guild.me.guild_permissions.view_audit_log:
                    async for entry in guild.audit_logs(
                        limit=1, action=AuditLogAction.unban
                    ):
                        if entry.target.id == user.id:
                            moderator = entry.user
                            reason = entry.reason
                            break

                embed = Embed(title="Member Unbanned", color=Color.green())
                embed.add_field(
                    name="Unbanned user",
                    value=f"{user.display_name} ({user.name}; {user.id})",
                )

                embed.add_field(
                    name="Unbanned by",
                    value=moderator.mention if moderator else "Unknown",
                )
                embed.add_field(
                    name="Reason of unban",
                    value=reason if reason else "*Not specified*",
                )
                await send_message_to_log_channel(c, guild, "member_unban", embed)
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_guild_channel_update(self, before: GuildChannel, after: GuildChannel):
        with engine.begin() as c:
            try:
                moderator = None
                if before.guild.me.guild_permissions.view_audit_log:
                    async for entry in before.guild.audit_logs(
                        limit=1, action=AuditLogAction.channel_update
                    ):
                        if entry.target.id == after.id:
                            moderator = entry.user

                embed = Embed(
                    title="Channel Edited",
                    color=Color.blue(),
                )
                embed.add_field(name="Channel", value=after.mention)

                if before.name != after.name:
                    embed.add_field(
                        name="Name",
                        value=f"{before.name} -> {after.name}",
                    )

                before_topic = getattr(before, "topic", None)
                after_topic = getattr(after, "topic", None)

                if hasattr(before, "topic") or hasattr(after, "topic"):
                    if before_topic != after_topic:
                        # Before topic
                        before_topic = (
                            before_topic if hasattr(before, "topic") else "*Empty*"
                        )

                        # After topic
                        after_topic = (
                            after_topic if hasattr(after, "topic") else "*Empty*"
                        )

                        # Add field
                        embed.add_field(
                            name="Topic",
                            value=f"{before_topic} -> {after_topic}",
                        )

                if before.category != after.category:
                    before_category = (
                        before.category.name
                        if before.category is not None
                        else "No category"
                    )
                    after_category = (
                        after.category.name
                        if after.category is not None
                        else "No category"
                    )
                    embed.add_field(
                        name="Category",
                        value=f"{before_category} -> {after_category}",
                    )

                if before.permissions_synced != after.permissions_synced:
                    embed.add_field(
                        name="Permissions Synced",
                        value=f"{before.permissions_synced} -> {after.permissions_synced}",
                    )

                if before.overwrites != after.overwrites:
                    for overwrite in before.overwrites:
                        if overwrite not in after.overwrites:
                            embed.add_field(
                                name="Override Removed",
                                value=overwrite.mention,
                            )

                    for overwrite in after.overwrites:
                        if overwrite not in before.overwrites:
                            embed.add_field(
                                name="Override Added",
                                value=overwrite.mention,
                            )

                    for i in after.overwrites.keys():
                        if i not in before.overwrites.keys():
                            continue

                        if before.overwrites[i] == after.overwrites[i]:
                            continue

                        allow: list[tuple[str, str, str]] = []
                        deny: list[tuple[str, str, str]] = []
                        neutral: list[tuple[str, str, str]] = []

                        for j in zip(before.overwrites.get(i), after.overwrites.get(i)):
                            if j[0][1] != j[1][1]:
                                if j[1][1] is None:
                                    neutral.append(
                                        (
                                            format_perm_name(j[0][0]),
                                            format_overwrite(j[0][1]),
                                            format_overwrite(j[1][1]),
                                        )
                                    )
                                elif j[1][1]:
                                    allow.append(
                                        (
                                            format_perm_name(j[0][0]),
                                            format_overwrite(j[0][1]),
                                            format_overwrite(j[1][1]),
                                        )
                                    )
                                elif not j[1][1]:
                                    deny.append(
                                        (
                                            format_perm_name(j[0][0]),
                                            format_overwrite(j[0][1]),
                                            format_overwrite(j[1][1]),
                                        )
                                    )

                        changes_str = ""

                        for j in allow:
                            changes_str += f"{j[0]}: {j[1]} -> {j[2]}"

                        for j in deny:
                            changes_str += f"{j[0]}: {j[1]} -> {j[2]}"

                        for j in neutral:
                            changes_str += f"{j[0]}: {j[1]} -> {j[2]}"

                        overwrite_embed = Embed(
                            title=f"Permission Override in {after.mention} Updated For {i.mention}",
                            color=Color.blue(),
                        )

                        overwrite_embed.add_field(
                            name="Permission Changes",
                            value=changes_str,
                        )

                        overwrite_embed.add_field(
                            name="Edited by",
                            value=moderator.mention if moderator else "Unknown",
                        )

                        await send_message_to_log_channel(
                            c, after.guild, "channel_update", overwrite_embed
                        )

                if len(embed.fields) > 1:
                    embed.add_field(
                        name="Edited by",
                        value=moderator.mention if moderator else "Unknown",
                    )
                    await send_message_to_log_channel(
                        c, after.guild, "channel_update", embed
                    )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_guild_channel_create(self, channel: GuildChannel):
        with engine.begin() as c:
            try:
                moderator = None
                if channel.guild.me.guild_permissions.view_audit_log:
                    async for entry in channel.guild.audit_logs(
                        limit=1, action=AuditLogAction.channel_create
                    ):
                        if entry.target.id == channel.id:
                            moderator = entry.user

                embed = Embed(
                    title="Channel Created",
                    description=f'A new channel "{channel.name}" ({channel.mention}) was created.',
                    color=Color.green(),
                )

                embed.add_field(
                    name="Channel Creator",
                    value=moderator.mention if moderator else "Unknown",
                )

                await send_message_to_log_channel(
                    c, channel.guild, "channel_create", embed
                )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel):
        with engine.begin() as c:
            try:
                moderator = None
                if channel.guild.me.guild_permissions.view_audit_log:
                    async for entry in channel.guild.audit_logs(
                        limit=1, action=AuditLogAction.channel_delete
                    ):
                        if entry.target.id == channel.id:
                            moderator = entry.user

                embed = Embed(
                    title="Channel Deleted",
                    description=f'Channel "{channel.name}" was deleted.',
                    color=Color.red(),
                )

                embed.add_field(
                    name="Deleted by",
                    value=moderator.mention if moderator else "Unknown",
                )

                await send_message_to_log_channel(
                    c, channel.guild, "channel_delete", embed
                )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_guild_update(self, before: Guild, after: Guild):
        with engine.begin() as c:
            try:
                moderator = None
                if after.me.guild_permissions.view_audit_log:
                    async for entry in after.audit_logs(
                        limit=1, action=AuditLogAction.guild_update
                    ):
                        moderator = entry.user

                embed = Embed(title="The server was updated", color=Color.blue())

                if before.name != after.name:
                    embed.add_field(
                        name="Server name",
                        value=f"{before.name} -> {after.name}",
                    )
                if before.icon != after.icon:
                    embed.add_field(
                        name="Server Icon",
                        value="Changed",
                    )
                if before.banner != after.banner:
                    embed.add_field(
                        name="Server Banner",
                        value="Changed",
                    )
                if before.description != after.description:
                    embed.add_field(
                        name="Server Description",
                        value=f"{before.description} -> {after.description}",
                    )
                if before.afk_channel != after.afk_channel:
                    embed.add_field(
                        name="AFK Channel",
                        value=f"{before.afk_channel} -> {after.afk_channel}",
                    )
                if before.afk_timeout != after.afk_timeout:
                    embed.add_field(
                        name="AFK Timeout",
                        value=f"{before.afk_timeout}s -> {after.afk_timeout}s",
                    )
                if before.system_channel != after.system_channel:
                    embed.add_field(
                        name="Welcome & Boosts Channel",
                        value=f"{before.system_channel} -> {after.system_channel}",
                    )
                if before.rules_channel != after.rules_channel:
                    embed.add_field(
                        name="Rules Channel",
                        value=f"{before.rules_channel} -> {after.rules_channel}",
                    )
                if before.public_updates_channel != after.public_updates_channel:
                    embed.add_field(
                        name="Discord Updates Channel",
                        value=f"{before.public_updates_channel} -> {after.public_updates_channel}",
                    )
                if before.preferred_locale != after.preferred_locale:
                    embed.add_field(
                        name="Preferred Language",
                        value=f"{before.preferred_locale} -> {after.preferred_locale}",
                    )
                if before.owner != after.owner:
                    embed.add_field(
                        name="Owner",
                        value=f"{before.owner} -> {after.owner}",
                    )
                if before.nsfw_level != after.nsfw_level:
                    before_nsfw_level = "Default"
                    if before.nsfw_level == NSFWLevel.safe:
                        before_nsfw_level = "Safe"
                    elif before.nsfw_level == NSFWLevel.age_restricted:
                        before_nsfw_level = "Age Restricted"
                    elif before.nsfw_level == NSFWLevel.explicit:
                        before_nsfw_level = "Explicit"

                    after_nsfw_level = "Default"
                    if after.nsfw_level == NSFWLevel.safe:
                        after_nsfw_level = "Safe"
                    elif after.nsfw_level == NSFWLevel.age_restricted:
                        after_nsfw_level = "Age Restricted"
                    elif after.nsfw_level == NSFWLevel.explicit:
                        after_nsfw_level = "Explicit"

                    embed.add_field(
                        name="NSFW Level",
                        value=f"{before_nsfw_level} -> {after_nsfw_level}",
                    )
                if before.verification_level != after.verification_level:
                    before_verification_level = "None"
                    if before.verification_level == VerificationLevel.low:
                        before_verification_level = "Low"
                    elif before.verification_level == VerificationLevel.medium:
                        before_verification_level = "Medium"
                    elif before.verification_level == VerificationLevel.high:
                        before_verification_level = "High"
                    elif before.verification_level == VerificationLevel.highest:
                        before_verification_level = "Highest"

                    after_verification_level = "None"
                    if after.verification_level == VerificationLevel.low:
                        after_verification_level = "Low"
                    elif after.verification_level == VerificationLevel.medium:
                        after_verification_level = "Medium"
                    elif after.verification_level == VerificationLevel.high:
                        after_verification_level = "High"
                    elif after.verification_level == VerificationLevel.highest:
                        after_verification_level = "Highest"

                    embed.add_field(
                        name="Verification Level",
                        value=f"{before_verification_level} -> {after_verification_level}",
                    )
                if before.explicit_content_filter != after.explicit_content_filter:
                    before_explicit_content_filter = "Disabled"
                    if before.explicit_content_filter == ContentFilter.no_role:
                        before_explicit_content_filter = "No role"
                    elif before.explicit_content_filter == ContentFilter.all_members:
                        before_explicit_content_filter = "All members"
                    after_explicit_content_filter = "Disabled"
                    if after.explicit_content_filter == ContentFilter.no_role:
                        after_explicit_content_filter = "No role"
                    elif after.explicit_content_filter == ContentFilter.all_members:
                        after_explicit_content_filter = "All members"

                    embed.add_field(
                        name="Explicit Content Filter",
                        value=f"{before_explicit_content_filter} -> {after_explicit_content_filter}",
                    )
                if before.default_notifications != after.default_notifications:
                    before_default_notifications = "None"
                    if before.default_notifications == NotificationLevel.only_mentions:
                        before_default_notifications = "Only mentions"
                    elif before.default_notifications == NotificationLevel.all_messages:
                        before_default_notifications = "All members"

                    after_default_notifications = "None"
                    if after.default_notifications == NotificationLevel.only_mentions:
                        after_default_notifications = "Only mentions"
                    elif after.default_notifications == NotificationLevel.all_messages:
                        after_default_notifications = "All members"

                    embed.add_field(
                        name="Default Notifications",
                        value=f"{before_default_notifications} -> {after_default_notifications}",
                    )
                if before.mfa_level != after.mfa_level:
                    embed.add_field(
                        name="2FA Level for Moderators",
                        value=f"{'Required' if before.mfa_level == 1 else 'Off'} -> {'Required' if after.mfa_level == 1 else 'Off'}",
                    )

                if len(embed.fields) > 0:
                    embed.add_field(
                        name="Edited by",
                        value=moderator.mention if moderator else "Unknown",
                    )

                    await send_message_to_log_channel(c, after, "guild_update", embed)
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_guild_role_create(self, role: Role):
        with engine.begin() as c:
            try:
                moderator = None
                if role.guild.me.guild_permissions.view_audit_log:
                    async for entry in role.guild.audit_logs(
                        limit=1, action=AuditLogAction.role_create
                    ):
                        if entry.target.id == role.id:
                            moderator = entry.user

                embed = Embed(
                    title="Role Created",
                    description=f'A new role "{role.name}" was created.',
                    color=Color.green(),
                )

                embed.add_field(
                    name="Created by",
                    value=moderator.mention if moderator else "Unknown",
                )

                await send_message_to_log_channel(c, role.guild, "role_create", embed)
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_guild_role_delete(self, role: Role):
        with engine.begin() as c:
            try:
                if (
                    role.guild.self_role is not None
                    and role.guild.self_role.id == role.id
                ):
                    return  # avoid "Unknown Guild" when bot gets kicked

                moderator = None
                if role.guild.me.guild_permissions.view_audit_log:
                    async for entry in role.guild.audit_logs(
                        limit=1, action=AuditLogAction.role_delete
                    ):
                        if entry.target.id == role.id:
                            moderator = entry.user

                embed = Embed(
                    title="Role Deleted",
                    description=f'A role "{role.name}" was deleted.',
                    color=Color.red(),
                )

                embed.add_field(
                    name="Deleted by",
                    value=moderator.mention if moderator else "Unknown",
                )

                await send_message_to_log_channel(c, role.guild, "role_delete", embed)
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_guild_role_update(self, before: Role, after: Role):
        with engine.begin() as c:
            try:
                moderator = None
                if after.guild.me.guild_permissions.view_audit_log:
                    async for entry in after.guild.audit_logs(
                        limit=1, action=AuditLogAction.role_update
                    ):
                        if entry.target.id == after.id:
                            moderator = entry.user

                embed = Embed(
                    title="Role Edited",
                    color=Color.blue(),
                )
                if before.name != after.name:
                    embed.add_field(
                        name="Name",
                        value=f"{before.name} -> {after.name}",
                    )
                if before.color != after.color:
                    embed.add_field(
                        name="Color",
                        value=f"{before.color} -> {after.color}",
                    )
                if before.hoist != after.hoist:
                    embed.add_field(
                        name="Show members separately",
                        value=f"{before.hoist} -> {after.hoist}",
                    )
                if before.mentionable != after.mentionable:
                    embed.add_field(
                        name="Allow mentioning",
                        value=f"{before.mentionable} -> {after.mentionable}",
                    )
                if before.permissions != after.permissions:
                    changed_deny: list[str] = []
                    changed_allow: list[str] = []

                    for perm, value in iter(after.permissions):
                        if value == dict(before.permissions)[perm]:
                            continue
                        if dict(before.permissions)[perm]:
                            changed_deny.append(perm)
                        else:
                            changed_allow.append(perm)

                    changed_deny = [format_perm_name(perm) for perm in changed_deny]
                    changed_allow = [format_perm_name(perm) for perm in changed_allow]

                    if len(changed_allow) > 0:
                        embed.add_field(
                            name="Allowed Permissions",
                            value=", ".join(changed_allow),
                        )
                    if len(changed_deny) > 0:
                        embed.add_field(
                            name="Denied Permissions",
                            value=", ".join(changed_deny),
                        )

                if len(embed.fields) > 0:
                    embed.add_field(
                        name="Edited by",
                        value=moderator.mention if moderator else "Unknown",
                    )

                    await send_message_to_log_channel(
                        c, after.guild, "role_update", embed
                    )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_invite_create(self, invite: Invite):
        if not isinstance(invite.guild, Guild):
            return

        with engine.begin() as c:
            try:
                moderator = None
                if invite.guild.me.guild_permissions.view_audit_log:
                    async for entry in invite.guild.audit_logs(
                        limit=1, action=AuditLogAction.invite_create
                    ):
                        if entry.target.id == invite.id:
                            moderator = entry.user

                embed = Embed(
                    title="Invite Created",
                    color=Color.green(),
                )
                embed.add_field(name="Code", value=invite.code)
                embed.add_field(
                    name="Channelo",
                    value=invite.channel.mention,
                )
                embed.add_field(
                    name="Max Uses",
                    value=str(invite.max_uses),
                )
                embed.add_field(
                    name="Expiry Age",
                    value=str(invite.max_age),
                )
                embed.add_field(
                    name="Is temporary?",
                    value=str(invite.temporary),
                )
                embed.add_field(
                    name="Created by",
                    value=moderator.mention if moderator else "Unknown",
                )
                await send_message_to_log_channel(
                    c, invite.guild, "invite_create", embed
                )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_invite_delete(self, invite: Invite):
        if not isinstance(invite.guild, Guild):
            return

        with engine.begin() as c:
            try:
                moderator = None
                if invite.guild.me.guild_permissions.view_audit_log:
                    async for entry in invite.guild.audit_logs(
                        limit=1, action=AuditLogAction.invite_delete
                    ):
                        if entry.target.id == invite.id:
                            moderator = entry.user

                embed = Embed(
                    title="Invite Deleted",
                    color=Color.red(),
                )

                embed.add_field(name="Code", value=invite.code)
                embed.add_field(
                    name="Channel",
                    value=invite.channel.mention,
                )
                embed.add_field(
                    name="Deleted by",
                    value=moderator.mention if moderator else "Unknown",
                )
                await send_message_to_log_channel(
                    c, invite.guild, "invite_delete", embed
                )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_member_join(self, member: Member):
        with engine.begin() as c:
            try:
                embed = Embed(
                    title="Member Joined",
                    description=f"The member {member.mention} joined the server.",
                    color=Color.green(),
                )
                await send_message_to_log_channel(c, member.guild, "member_join", embed)
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        with engine.begin() as c:
            try:
                embed = Embed(
                    title="Member Left",
                    description=f"The member {member.mention} left the server.",
                    color=Color.red(),
                )
                await send_message_to_log_channel(
                    c, member.guild, "member_leave", embed
                )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        with engine.begin() as c:
            try:
                if after.id == after.guild.me.id:
                    return  # avoid "Unknown Guild" when the self member gets banned

                moderator = None
                if after.guild.me.guild_permissions.view_audit_log:
                    async for entry in after.guild.audit_logs(
                        limit=1, action=AuditLogAction.member_update
                    ):
                        if entry.target.id == after.id:
                            moderator = entry.user

                embed = Embed(
                    title="Member Updated",
                    color=Color.blue(),
                )
                embed.add_field(name="User", value=after.mention)

                if before.nick != after.nick:
                    embed.add_field(
                        name="Nickname",
                        value=f"{before.nick} -> {after.nick}",
                    )
                if before.roles != after.roles:
                    added_roles = [
                        role.mention for role in after.roles if role not in before.roles
                    ]
                    removed_roles = [
                        role.mention for role in before.roles if role not in after.roles
                    ]
                    if len(added_roles) > 0:
                        embed.add_field(
                            name="Added Roles",
                            value=", ".join(added_roles),
                        )
                    if len(removed_roles) > 0:
                        embed.add_field(
                            name="Removed Roles",
                            value=", ".join(removed_roles),
                        )

                if len(embed.fields) > 1:
                    embed.add_field(
                        name="Updated by",
                        value=moderator.mention if moderator else "Unknown",
                    )
                    await send_message_to_log_channel(
                        c, after.guild, "member_update", embed
                    )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_voice_state_update(
        self, member: Member, before: VoiceState, after: VoiceState
    ):
        with engine.begin() as c:
            try:
                if before.channel is None and after.channel is not None:
                    # joined a channel
                    embed = Embed(
                        title="User joined Voice Channel",
                        description=f"The member {member.mention} joined the voice channel {after.channel.mention}.",
                        color=Color.green(),
                    )
                    await send_message_to_log_channel(
                        c, member.guild, "voice_join", embed
                    )

                if before.channel is not None and after.channel is None:
                    # left a channel
                    embed = Embed(
                        title="User left Voice Channel",
                        description=f"The member {member.mention} left the voice channel {before.channel.mention}.",
                        color=Color.red(),
                    )
                    await send_message_to_log_channel(
                        c, member.guild, "voice_leave", embed
                    )

                if before.channel is not None and after.channel is not None:
                    # moved to a different channel or was muted/deafened by admin
                    if before.channel != after.channel:
                        embed = Embed(
                            title="User moved Voice Channels",
                            description=f"Member {member.mention} moved from {before.channel.mention} to {after.channel.mention}.",
                            color=Color.blue(),
                        )
                        await send_message_to_log_channel(
                            c, member.guild, "voice_move", embed
                        )
                        return

                    if before.mute != after.mute:
                        mod = None
                        if member.guild.me.guild_permissions.view_audit_log:
                            async for entry in member.guild.audit_logs(
                                limit=1, action=AuditLogAction.member_update
                            ):
                                if entry.target.id == member.id:
                                    mod = entry.user
                                    break

                        embed = Embed(
                            title="User Server Muted",
                            color=Color.blue(),
                        )

                        if after.mute:
                            embed.description = (
                                f"The member {member.mention} was server muted."
                            )
                        else:
                            embed.description = (
                                f"The member {member.mention} was server unmuted."
                            )

                        if mod:
                            embed.add_field(
                                name="Moderator",
                                value=mod.mention,
                            )
                        await send_message_to_log_channel(
                            c, member.guild, "voice_mute", embed
                        )

                    if before.deaf != after.deaf:
                        mod = None
                        if member.guild.me.guild_permissions.view_audit_log:
                            async for entry in member.guild.audit_logs(
                                limit=1, action=AuditLogAction.member_update
                            ):
                                if entry.target.id == member.id:
                                    mod = entry.user
                                    break

                        embed = Embed(
                            title="User Server Deafened",
                            color=Color.blue(),
                        )

                        if after.deaf:
                            embed.description = (
                                f"The member {member.mention} was server deafened."
                            )
                        else:
                            embed.description = (
                                f"The member {member.mention} was server undeafened."
                            )

                        if mod:
                            embed.add_field(
                                name="Moderator",
                                value=mod.mention,
                            )
                        await send_message_to_log_channel(
                            c, member.guild, "voice_deafen", embed
                        )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_reaction_add(self, reaction: Reaction, user: User):
        if not isinstance(reaction.message.guild, Guild):
            return

        with engine.begin() as c:
            try:
                embed = Embed(
                    title="Reaction Added",
                    color=Color.green(),
                )
                embed.add_field(
                    name="Message",
                    value=f"[jump](<{reaction.message.jump_url}>)",
                )
                embed.add_field(
                    name="Reaction",
                    value=str(reaction.emoji),
                )
                embed.add_field(
                    name="User",
                    value=user.mention,
                )
                await send_message_to_log_channel(
                    c, reaction.message.guild, "reaction_add", embed
                )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_reaction_remove(self, reaction: Reaction, user: User):
        if not isinstance(reaction.message.guild, Guild):
            return

        with engine.begin() as c:
            try:
                embed = Embed(
                    title="Reaction Removed",
                    color=Color.red(),
                )
                embed.add_field(
                    name="Message",
                    value=f"[jump](<{reaction.message.jump_url}>)",
                )
                embed.add_field(
                    name="Reaction",
                    value=str(reaction.emoji),
                )
                embed.add_field(
                    name="User",
                    value=user.mention,
                )
                await send_message_to_log_channel(
                    c, reaction.message.guild, "reaction_remove", embed
                )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_reaction_clear(self, message: Message, reactions: list[Reaction]):
        if not isinstance(message.guild, Guild):
            return

        with engine.begin() as c:
            try:
                if len(reactions) < 1:
                    return
                embed = Embed(
                    title="Reactions Cleared",
                    color=Color.red(),
                )
                embed.add_field(
                    name="Message",
                    value=reactions[0].message.jump_url,
                )
                await send_message_to_log_channel(
                    c, message.guild, "reaction_clear_all", embed
                )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_reaction_clear_emoji(self, reaction: Reaction):
        if not isinstance(reaction.message.guild, Guild):
            return

        with engine.begin() as c:
            try:
                embed = Embed(
                    title="Reactions Cleared for Emoji",
                    color=Color.red(),
                )
                embed.add_field(
                    name="Message",
                    value=reaction.message.jump_url,
                )
                embed.add_field(
                    name="Emoji",
                    value=str(reaction.emoji),
                )
                await send_message_to_log_channel(
                    c, reaction.message.guild, "reaction_clear_emoji", embed
                )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_scheduled_event_create(self, event: ScheduledEvent):
        with engine.begin() as c:
            try:
                moderator = None
                if event.guild.me.guild_permissions.view_audit_log:
                    async for entry in event.guild.audit_logs(
                        limit=1, action=AuditLogAction.scheduled_event_create
                    ):
                        moderator = entry.user

                embed = Embed(
                    title="Event Created",
                    color=Color.green(),
                )
                embed.add_field(name="Name", value=event.name)
                embed.add_field(
                    name="Description",
                    value=event.description
                    if event.description is not None
                    else "*Empty*",
                )
                embed.add_field(
                    name="Location",
                    value=event.location.value,
                )
                embed.add_field(
                    name="Start",
                    value=event.start_time.strftime("%Y/%m/%d %H:%M:%S"),
                )
                if event.end_time is not None:
                    embed.add_field(
                        name="End",
                        value=event.end_time.strftime("%Y/%m/%d %H:%M:%S"),
                    )
                else:
                    embed.add_field(name="End", value="N/A")
                embed.add_field(
                    name="Created by",
                    value=moderator.mention if moderator else "Unknown",
                )
                await send_message_to_log_channel(c, event.guild, "event_create", embed)
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_scheduled_event_update(
        self, before: ScheduledEvent, after: ScheduledEvent
    ):
        with engine.begin() as c:
            try:
                moderator = None
                if after.guild.me.guild_permissions.view_audit_log:
                    async for entry in after.guild.audit_logs(
                        limit=1, action=AuditLogAction.scheduled_event_update
                    ):
                        moderator = entry.user

                embed = Embed(
                    title="Event Updated",
                    color=Color.blue(),
                )

                if before.name != after.name:
                    embed.add_field(
                        name="Name",
                        value=f"{before.name} -> {after.name}",
                    )
                if before.description != after.description:
                    embed.add_field(
                        name="Description",
                        value=f"{before.description} -> {after.description}",
                    )
                if before.location != after.location:
                    embed.add_field(
                        name="Location",
                        value=f"{before.location.value} -> {after.location.value}",
                    )
                if before.start_time != after.start_time:
                    embed.add_field(
                        name="Start",
                        value=f"{before.start_time.strftime('%Y/%m/%d %H:%M:%S')} -> {after.start_time.strftime('%Y/%m/%d %H:%M:%S')}",
                    )
                if before.end_time != after.end_time:
                    embed.add_field(
                        name="End",
                        value=f"{before.end_time.strftime('%Y/%m/%d %H:%M:%S') if before.end_time is not None else 'N/A'} -> {after.end_time.strftime('%Y/%m/%d %H:%M:%S') if after.end_time is not None else 'N/A'}",
                    )
                if len(embed.fields) > 0:
                    embed.add_field(
                        name="Updated by",
                        value=moderator.mention if moderator else "Unknown",
                    )
                    await send_message_to_log_channel(
                        c, after.guild, "event_update", embed
                    )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_scheduled_event_delete(self, event: ScheduledEvent):
        with engine.begin() as c:
            try:
                moderator = None
                if event.guild.me.guild_permissions.view_audit_log:
                    async for entry in event.guild.audit_logs(
                        limit=1, action=AuditLogAction.scheduled_event_delete
                    ):
                        moderator = entry.user

                embed = Embed(
                    title="Event Deleted",
                    color=Color.red(),
                )
                embed.add_field(name="Name", value=event.name)
                embed.add_field(
                    name="Description",
                    value=event.description
                    if event.description is not None
                    else "*Empty*",
                )
                embed.add_field(
                    name="Location",
                    value=event.location.value,
                )
                embed.add_field(
                    name="Start",
                    value=event.start_time.strftime("%Y/%m/%d %H:%M:%S"),
                )
                if event.end_time is not None:
                    embed.add_field(
                        name="End",
                        value=event.end_time.strftime("%Y/%m/%d %H:%M:%S"),
                    )
                embed.add_field(
                    name="Deleted by",
                    value=moderator.mention if moderator else "Unknown",
                )
                await send_message_to_log_channel(c, event.guild, "event_delete", embed)
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_thread_create(self, thread: Thread):
        with engine.begin() as c:
            try:
                moderator = None
                if thread.guild.me.guild_permissions.view_audit_log:
                    async for entry in thread.guild.audit_logs(
                        limit=1, action=AuditLogAction.thread_create
                    ):
                        if entry.target.id == thread.id:
                            moderator = entry.user

                embed = Embed(
                    title="Thread Created",
                    description=f'The thread "{thread.name}" was created',
                    color=Color.green(),
                )
                embed.add_field(
                    name="Jump to thread",
                    value=f"[jump](<{thread.jump_url}>)",
                )
                embed.add_field(name="Name", value=thread.name)
                embed.add_field(
                    name="Created by",
                    value=moderator.mention if moderator else "Unknown",
                )
                await send_message_to_log_channel(
                    c, thread.guild, "thread_create", embed
                )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_thread_delete(self, thread: Thread):
        with engine.begin() as c:
            try:
                moderator = None
                if thread.guild.me.guild_permissions.view_audit_log:
                    async for entry in thread.guild.audit_logs(
                        limit=1, action=AuditLogAction.thread_delete
                    ):
                        if entry.target.id == thread.id:
                            moderator = entry.user

                embed = Embed(
                    title="Thread Deleted",
                    description=f'The thread "{thread.name}" was deleted.',
                    color=Color.red(),
                )
                embed.add_field(
                    name="Deleted by",
                    value=moderator.mention if moderator else "Unknown",
                )
                await send_message_to_log_channel(
                    c, thread.guild, "thread_delete", embed
                )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")

    @Cog.listener()
    async def on_thread_update(self, before: Thread, after: Thread):
        with engine.begin() as c:
            try:
                moderator = None
                if before.guild.me.guild_permissions.view_audit_log:
                    async for entry in before.guild.audit_logs(
                        limit=1, action=AuditLogAction.thread_update
                    ):
                        if entry.target.id == after.id:
                            moderator = entry.user

                embed = Embed(
                    title="Thread Updated",
                    color=Color.blue(),
                )

                if before.name != after.name:
                    embed.add_field(
                        name="Name",
                        value=f"{before.name} -> {after.name}",
                    )
                if before.archived != after.archived:
                    embed.add_field(
                        name="Archived",
                        value=f"{before.archived} -> {after.archived}",
                    )
                if before.locked != after.locked:
                    embed.add_field(
                        name="Locked",
                        value=f"{before.locked} -> {after.locked}",
                    )
                if len(embed.fields) > 0:
                    embed.add_field(
                        name="Jump to thread",
                        value=f"[jump](<{after.jump_url}>)",
                    )
                    embed.add_field(
                        name="Moderator",
                        value=moderator.mention if moderator else "Unknown",
                    )
                    await send_message_to_log_channel(
                        c, after.guild, "thread_update", embed
                    )
            except Exception as e:
                akabot_logger.exception(f"Failed to handle log event: {e}")


def setup(bot: Bot):
    bot.add_cog(Logging(bot))
