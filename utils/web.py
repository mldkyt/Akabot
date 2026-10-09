import datetime
import random
import string

import sentry_sdk
from discord import Guild, Member
from sqlalchemy import Connection, delete, insert, select, update

from database import (
    engine,
    synced_automod_rules,
    synced_channels,
    synced_emojis,
    synced_roles,
    web_tokens,
)
from logger import akabot_logger
from utils.automod_actions import setting_automod_sync_error
from utils.reaction_roles import update_bot_permission


async def sync_text_channels(c: Connection, guild: Guild):
    db_text_channels = [
        int(i[0])
        for i in c.execute(
            select(synced_channels.c.cid).where(
                (synced_channels.c.gid == str(guild.id))
                & (synced_channels.c.ctype == "text")
            )
        ).fetchall()
    ]
    guild_text_channels = [i.id for i in guild.text_channels]

    to_remove = [i for i in db_text_channels if i not in guild_text_channels]

    for channel in to_remove:
        c.execute(
            delete(synced_channels).where(
                (synced_channels.c.gid == str(guild.id))
                & (synced_channels.c.cid == str(channel))
            )
        )

    for channel in guild.text_channels:
        if (
            c.execute(
                select(synced_channels).where(
                    (synced_channels.c.gid == str(guild.id))
                    & (synced_channels.c.cid == str(channel.id))
                )
            ).fetchone()
            is None
        ):
            c.execute(
                insert(synced_channels).values(
                    gid=str(guild.id),
                    cid=str(channel.id),
                    cname=channel.name,
                    ctype="text",
                )
            )
        else:
            c.execute(
                update(synced_channels)
                .where(
                    (synced_channels.c.gid == str(guild.id))
                    & (synced_channels.c.cid == str(channel.id))
                )
                .values(cname=channel.name, ctype="text")
            )


async def sync_voice_channels(c: Connection, guild: Guild):
    db_voice_channels = [
        int(i[0])
        for i in c.execute(
            select(synced_channels.c.cid).where(
                (synced_channels.c.gid == str(guild.id))
                & (synced_channels.c.ctype == "voice")
            )
        ).fetchall()
    ]
    guild_voice_channels = [i.id for i in guild.voice_channels]

    to_remove = [i for i in db_voice_channels if i not in guild_voice_channels]

    for channel in to_remove:
        c.execute(
            delete(synced_channels).where(
                (synced_channels.c.gid == str(guild.id))
                & (synced_channels.c.cid == str(channel))
            )
        )

    for channel in guild.voice_channels:
        if (
            c.execute(
                select(synced_channels).where(
                    (synced_channels.c.gid == str(guild.id))
                    & (synced_channels.c.cid == str(channel.id))
                )
            ).fetchone()
            is None
        ):
            c.execute(
                insert(synced_channels).values(
                    gid=str(guild.id),
                    cid=str(channel.id),
                    cname=channel.name,
                    ctype="voice",
                )
            )
        else:
            c.execute(
                update(synced_channels)
                .where(
                    (synced_channels.c.gid == str(guild.id))
                    & (synced_channels.c.cid == str(channel.id))
                )
                .values(cname=channel.name, ctype="voice")
            )


async def sync_roles(c: Connection, guild: Guild):
    db_roles = [
        int(i[0])
        for i in c.execute(
            select(synced_roles.c.rid).where(synced_roles.c.gid == str(guild.id))
        ).fetchall()
    ]
    guild_roles = [i.id for i in guild.roles]

    to_remove = [i for i in db_roles if i not in guild_roles]

    for role in to_remove:
        c.execute(
            delete(synced_roles).where(
                (synced_roles.c.gid == str(guild.id))
                & (synced_roles.c.rid == str(role))
            )
        )

    for role in guild.roles:
        if (
            c.execute(
                select(synced_roles).where(
                    (synced_roles.c.gid == str(guild.id))
                    & (synced_roles.c.rid == str(role.id))
                )
            ).fetchone()
            is None
        ):
            c.execute(
                insert(synced_roles).values(
                    gid=str(guild.id), rid=str(role.id), rname=role.name
                )
            )
        else:
            c.execute(
                update(synced_roles)
                .where(
                    (synced_roles.c.gid == str(guild.id))
                    & (synced_roles.c.rid == str(role.id))
                )
                .values(rname=role.name)
            )


async def sync_emojis(c: Connection, guild: Guild):
    db_emojis = {
        i[0]: (i[1], i[2])
        for i in c.execute(
            select(
                synced_emojis.c.eid, synced_emojis.c.name, synced_emojis.c.animated
            ).where(synced_emojis.c.gid == str(guild.id))
        ).fetchall()
    }
    guild_emojis = {str(i.id): i for i in guild.emojis}

    for eid in db_emojis:
        if eid not in guild_emojis:
            c.execute(
                delete(synced_emojis).where(
                    (synced_emojis.c.gid == str(guild.id))
                    & (synced_emojis.c.eid == eid)
                )
            )

    for eid, emoji in guild_emojis.items():
        if eid in db_emojis:
            if db_emojis[eid] == (emoji.name, emoji.animated):
                continue

            c.execute(
                update(synced_emojis)
                .where(
                    (synced_emojis.c.gid == str(guild.id))
                    & (synced_emojis.c.eid == eid)
                )
                .values(name=emoji.name, animated=emoji.animated)
            )
        else:
            c.execute(
                insert(synced_emojis).values(
                    gid=str(guild.id),
                    eid=eid,
                    name=emoji.name,
                    animated=emoji.animated,
                )
            )


async def sync_automod_actions(c: Connection, guild: Guild):
    if not guild.me.guild_permissions.manage_guild:
        raise ValueError(
            f"Akabot is missing the Manage Server permission in {guild.name}"
        )

    automod_rules = await guild.fetch_auto_moderation_rules()
    automod_rule_ids = [i.id for i in automod_rules]
    db_automod_rules = [
        int(i[0])
        for i in c.execute(
            select(synced_automod_rules.c.aid).where(
                synced_automod_rules.c.gid == str(guild.id)
            )
        ).fetchall()
    ]

    to_remove = [i for i in db_automod_rules if i not in automod_rule_ids]

    for rule in to_remove:
        c.execute(
            delete(synced_automod_rules).where(
                (synced_automod_rules.c.gid == str(guild.id))
                & (synced_automod_rules.c.aid == rule)
            )
        )

    for rule in automod_rules:
        if (
            c.execute(
                select(synced_automod_rules).where(
                    (synced_automod_rules.c.gid == str(guild.id))
                    & (synced_automod_rules.c.aid == str(rule.id))
                )
            ).fetchone()
            is None
        ):
            c.execute(
                insert(synced_automod_rules).values(
                    gid=str(guild.id), aid=str(rule.id), aname=rule.name
                )
            )
        else:
            c.execute(
                update(synced_automod_rules)
                .where(
                    (synced_automod_rules.c.gid == str(guild.id))
                    & (synced_automod_rules.c.aid == str(rule.id))
                )
                .values(aname=rule.name)
            )


async def sync_guild(guild: Guild):
    try:
        with engine.begin() as c:
            await sync_text_channels(c, guild)
            await sync_voice_channels(c, guild)
            await sync_roles(c, guild)
            await sync_emojis(c, guild)
            update_bot_permission(c, guild)
            try:
                await sync_automod_actions(c, guild)
                setting_automod_sync_error.set(c, guild.id, "")
            except Exception as e:
                setting_automod_sync_error.set(c, guild.id, str(e))
                akabot_logger.warning(
                    f"Failed to sync automod actions for guild {guild.name}: {e}"
                )
    except Exception as e:
        akabot_logger.exception(f"Failed to sync guild {guild}: {e}")
        sentry_sdk.capture_exception(e)


def generate_token(guild: Guild, member: Member) -> str:
    token = "".join(random.choices(string.ascii_letters + string.digits, k=32))
    expires = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=2)

    with engine.begin() as c:
        c.execute(
            insert(web_tokens).values(
                gid=str(guild.id),
                gname=guild.name,
                uid=str(member.id),
                uname=member.display_name,
                uavatar=member.display_avatar.url,
                token=token,
                expires=expires,
            )
        )

    return token
