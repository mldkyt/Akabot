import re

from discord import (
    Bot,
    ButtonStyle,
    Interaction,
    InteractionType,
    Message,
    NotFound,
    PartialEmoji,
)
from discord.ui import ActionRow, Button, View
from sqlalchemy import Connection, delete, select, update

from database import engine, reaction_roles, reaction_roles_options
from logger import akabot_logger
from utils.message_appends import apply_appends
from utils.server_settings import ServerSetting, SettingType
from utils.tasks import register_task

CUSTOM_EMOJI_RE = re.compile(r"<(a)?:([^:]+):(\d+)>")

BUTTON_STYLES = {
    "primary": ButtonStyle.primary,
    "secondary": ButtonStyle.secondary,
    "success": ButtonStyle.success,
    "danger": ButtonStyle.danger,
}

setting_reaction_roles_bot_ok = ServerSetting(
    name="Reaction Roles: Bot can manage roles",
    setting_type=SettingType.NORMAL,
    default="true",
)


def parse_emoji(emoji: str | None):
    if not emoji:
        return None

    match = CUSTOM_EMOJI_RE.fullmatch(emoji.strip())
    if match is not None:
        return PartialEmoji(
            name=match.group(2), id=int(match.group(3)), animated=bool(match.group(1))
        )

    return emoji


def get_options(c: Connection, rr_id: int) -> list[dict]:
    rows = c.execute(
        select(
            reaction_roles_options.c.id,
            reaction_roles_options.c.style,
            reaction_roles_options.c.label,
            reaction_roles_options.c.emoji,
            reaction_roles_options.c.rid,
        )
        .where(reaction_roles_options.c.rr_id == rr_id)
        .order_by(reaction_roles_options.c.position, reaction_roles_options.c.id)
    ).fetchall()

    return [
        {
            "id": i[0],
            "style": i[1] or "primary",
            "label": i[2],
            "emoji": i[3],
            "rid": i[4],
        }
        for i in rows
    ]


def build_view(options: list[dict], guild) -> View:
    view = View()

    for option in options:
        role = guild.get_role(int(option["rid"])) if guild is not None else None
        label = option["label"] or (role.name if role is not None else "Role")

        emoji = parse_emoji(option["emoji"])
        if isinstance(emoji, PartialEmoji) and emoji.id is not None:
            if guild is None or guild.get_emoji(emoji.id) is None:
                emoji = None

        view.add_item(
            Button(
                style=BUTTON_STYLES.get(option["style"], ButtonStyle.primary),
                label=label,
                emoji=emoji,
                custom_id=f"rr-{option['id']}",
            )
        )

    return view


def update_bot_permission(c: Connection, guild) -> None:
    setting_reaction_roles_bot_ok.set(
        c, guild.id, str(bool(guild.me.guild_permissions.manage_roles)).lower()
    )


@register_task("reactionRoles_create")
async def handle_create(bot: Bot, data: dict) -> None:
    rr_id = data["id"]

    with engine.begin() as c:
        row = c.execute(
            select(reaction_roles).where(reaction_roles.c.id == rr_id)
        ).fetchone()
        if row is None:
            return

        options = get_options(c, rr_id)

    guild = bot.get_guild(int(row.gid))
    if guild is None:
        raise ValueError(f"Guild {row.gid} not found")

    update_bot_permission_if_possible(guild)

    channel = guild.get_channel(int(row.cid))
    if channel is None:
        raise ValueError(f"Channel {row.cid} not found")

    if not channel.permissions_for(guild.me).send_messages:
        raise ValueError(f"Missing send messages permission in {channel.name}")

    view = build_view(options, guild)
    message = await channel.send(content=row.content or "", view=view)

    with engine.begin() as c:
        c.execute(
            update(reaction_roles)
            .where(reaction_roles.c.id == rr_id)
            .values(mid=str(message.id))
        )


@register_task("reactionRoles_edit")
async def handle_edit(bot: Bot, data: dict) -> None:
    rr_id = data["id"]

    with engine.begin() as c:
        row = c.execute(
            select(reaction_roles).where(reaction_roles.c.id == rr_id)
        ).fetchone()
        if row is None:
            return

        options = get_options(c, rr_id)

    if row.mid is None:
        return

    guild = bot.get_guild(int(row.gid))
    if guild is None:
        raise ValueError(f"Guild {row.gid} not found")

    update_bot_permission_if_possible(guild)

    channel = guild.get_channel(int(row.cid))
    if channel is None:
        raise ValueError(f"Channel {row.cid} not found")

    try:
        message = await channel.fetch_message(int(row.mid))
    except NotFound:
        return

    view = build_view(options, guild)
    await message.edit(content=row.content or "", view=view)


@register_task("reactionRoles_delete")
async def handle_delete(bot: Bot, data: dict) -> None:
    mid = data.get("mid")
    if not mid:
        return

    guild = bot.get_guild(int(data["gid"]))
    if guild is None:
        return

    channel = guild.get_channel(int(data["cid"]))
    if channel is None:
        return

    try:
        message = await channel.fetch_message(int(mid))
    except NotFound:
        return

    await message.delete()


def update_bot_permission_if_possible(guild) -> None:
    try:
        with engine.begin() as c:
            update_bot_permission(c, guild)
    except Exception as e:
        akabot_logger.exception(f"Failed to sync reaction roles permission: {e}")


def delete_by_messages(message_ids: list[str]) -> None:
    if not message_ids:
        return

    with engine.begin() as c:
        ids = select(reaction_roles.c.id).where(reaction_roles.c.mid.in_(message_ids))
        c.execute(
            delete(reaction_roles_options).where(
                reaction_roles_options.c.rr_id.in_(ids)
            )
        )
        c.execute(delete(reaction_roles).where(reaction_roles.c.mid.in_(message_ids)))


def delete_by_channel(guild_id: str, channel_id: str) -> None:
    with engine.begin() as c:
        ids = select(reaction_roles.c.id).where(
            (reaction_roles.c.gid == guild_id) & (reaction_roles.c.cid == channel_id)
        )
        c.execute(
            delete(reaction_roles_options).where(
                reaction_roles_options.c.rr_id.in_(ids)
            )
        )
        c.execute(
            delete(reaction_roles).where(
                (reaction_roles.c.gid == guild_id)
                & (reaction_roles.c.cid == channel_id)
            )
        )


def get_roles(msg: Message):
    roles = []

    if msg.guild is None:
        return []

    for row in msg.components:
        if not isinstance(row, ActionRow):
            continue

        for item in row.children:
            if not isinstance(item, Button):
                continue

            split = item.custom_id.split("-")
            if len(split) != 2:
                continue

            if split[0] not in ["rrn", "rra", "rrr", "rrs"]:
                continue

            if not split[1].isdigit():
                continue

            role = msg.guild.get_role(int(split[1]))
            if role is None:
                continue

            roles.append(role)

    return roles


async def handle_interaction(bot: Bot, interaction: Interaction) -> None:
    try:
        if interaction.type != InteractionType.component:
            return

        custom_id = interaction.custom_id
        if custom_id is None:
            return

        if custom_id.startswith("rr-") and custom_id[3:].isdigit():
            await handle_db_interaction(interaction, int(custom_id[3:]))
            return

        await handle_legacy_interaction(interaction)
    except Exception as e:
        akabot_logger.exception(f"Failed to handle reaction role interaction: {e}")


async def handle_db_interaction(interaction: Interaction, option_id: int) -> None:
    with engine.begin() as c:
        option = c.execute(
            select(reaction_roles_options).where(
                reaction_roles_options.c.id == option_id
            )
        ).fetchone()
        if option is None:
            return

        rr = c.execute(
            select(reaction_roles).where(reaction_roles.c.id == option.rr_id)
        ).fetchone()
        if rr is None:
            return

        rr_type = rr.type
        siblings = [
            i[0]
            for i in c.execute(
                select(reaction_roles_options.c.rid).where(
                    reaction_roles_options.c.rr_id == option.rr_id
                )
            ).fetchall()
        ]

    if not interaction.guild.me.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "I do not have permissions to manage roles!", ephemeral=True
        )
        return

    role = interaction.guild.get_role(int(option.rid))
    if role is None:
        await interaction.response.send_message(
            "That role can no longer be found!", ephemeral=True
        )
        return

    if role.position >= interaction.guild.me.top_role.position:
        await interaction.response.send_message(
            "I cannot assign this role!", ephemeral=True
        )
        return

    if rr_type == "n":
        if role in interaction.user.roles:
            await interaction.response.send_message(
                apply_appends(
                    interaction.user.id,
                    f"Role {role.mention} has been removed from you!",
                ),
                ephemeral=True,
            )
            await interaction.user.remove_roles(role, reason="Reaction role")
        else:
            await interaction.response.send_message(
                apply_appends(
                    interaction.user.id,
                    f"Role {role.mention} has been added to you!",
                ),
                ephemeral=True,
            )
            await interaction.user.add_roles(role, reason="Reaction role")
        return

    if rr_type == "a":
        if role in interaction.user.roles:
            await interaction.response.send_message(
                apply_appends(interaction.user.id, "You already have this role!"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            apply_appends(
                interaction.user.id, f"Role {role.mention} has been added to you!"
            ),
            ephemeral=True,
        )
        await interaction.user.add_roles(role, reason="Reaction role")
        return

    if rr_type == "r":
        if role not in interaction.user.roles:
            await interaction.response.send_message(
                apply_appends(interaction.user.id, "You already don't have this role!"),
                ephemeral=True,
            )
            return

        await interaction.response.send_message(
            apply_appends(
                interaction.user.id, f"Role {role.mention} has been removed from you!"
            ),
            ephemeral=True,
        )
        await interaction.user.remove_roles(role, reason="Reaction role")
        return

    if rr_type == "s":
        if role in interaction.user.roles:
            await interaction.response.send_message(
                apply_appends(
                    interaction.user.id, f"You already have selected {role.mention}"
                ),
                ephemeral=True,
            )
            return

        roles = []
        for sibling in siblings:
            sibling_role = interaction.guild.get_role(int(sibling))
            if sibling_role is not None and sibling_role in interaction.user.roles:
                roles.append(sibling_role)

        await interaction.response.send_message(
            apply_appends(
                interaction.user.id,
                f"Role {role.mention} was selected out of a choice.",
            ),
            ephemeral=True,
        )

        if roles:
            await interaction.user.remove_roles(*roles, reason="Reaction role")

        await interaction.user.add_roles(role, reason="Reaction role")


async def handle_legacy_interaction(interaction: Interaction) -> None:
    split = interaction.custom_id.split("-")
    if len(split) != 2:
        return

    if split[0] not in ["rrn", "rra", "rrr", "rrs"]:
        return

    if not split[1].isdigit():
        return

    if not interaction.guild.me.guild_permissions.manage_roles:
        await interaction.response.send_message(
            "I do not have permissions to manage roles!", ephemeral=True
        )
        return

    role = interaction.guild.get_role(int(split[1]))
    if role is None:
        return

    if role.position >= interaction.guild.me.top_role.position:
        await interaction.response.send_message(
            "I cannot assign this role!", ephemeral=True
        )
        return

    if split[0] == "rrn":
        if role in interaction.user.roles:
            await interaction.response.send_message(
                apply_appends(
                    interaction.user.id,
                    f"Role {role.mention} has been removed from you!",
                ),
                ephemeral=True,
            )
            await interaction.user.remove_roles(role, reason="Reaction role")
            return
        if role not in interaction.user.roles:
            await interaction.response.send_message(
                apply_appends(
                    interaction.user.id,
                    f"Role {role.mention} has been added to you!",
                ),
                ephemeral=True,
            )
            await interaction.user.add_roles(role, reason="Reaction role")
            return

    if split[0] == "rra":
        if role in interaction.user.roles:
            await interaction.response.send_message(
                apply_appends(interaction.user.id, "You already have this role!"),
                ephemeral=True,
            )
            return
        if role not in interaction.user.roles:
            await interaction.response.send_message(
                apply_appends(
                    interaction.user.id,
                    f"Role {role.mention} has been added to you!",
                ),
                ephemeral=True,
            )
            await interaction.user.add_roles(role, reason="Reaction role")
            return

    if split[0] == "rrr":
        if role not in interaction.user.roles:
            await interaction.response.send_message(
                apply_appends(interaction.user.id, "You already don't have this role!"),
                ephemeral=True,
            )
            return
        if role in interaction.user.roles:
            await interaction.response.send_message(
                apply_appends(
                    interaction.user.id,
                    f"Role {role.mention} has been removed from you!",
                ),
                ephemeral=True,
            )
            await interaction.user.remove_roles(role, reason="Reaction role")
            return

    if split[0] == "rrs":
        if role in interaction.user.roles:
            await interaction.response.send_message(
                apply_appends(
                    interaction.user.id,
                    f"You already have selected {role.mention}",
                ),
                ephemeral=True,
            )
            return

        roles = get_roles(interaction.message)
        await interaction.response.send_message(
            apply_appends(
                interaction.user.id,
                f"Role {role.mention} was selected out of a choice.",
            ),
            ephemeral=True,
        )
        await interaction.user.remove_roles(*roles, reason="Reaction role")
        await interaction.user.add_roles(role, reason="Reaction role")
