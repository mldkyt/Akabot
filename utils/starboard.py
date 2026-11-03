import asyncio
import datetime

from discord import (
    Bot,
    Color,
    Embed,
    Forbidden,
    HTTPException,
    Message,
    NotFound,
)
from sqlalchemy import Connection, delete, insert, select

from database import engine, starboard_emojis, starboard_messages, starboards
from logger import akabot_logger
from utils.emoji import normalize_emoji
from utils.server_settings import KV
from utils.tasks import register_task

MAX_EMOJIS = 20
MIN_MIN_COUNT = 1
MAX_MIN_COUNT = 1000

setting_starboard_bot_ok = KV(
    name="Starboards: Bot can post",
    default="true",
)

_message_locks: dict[str, asyncio.Lock] = {}


def _message_lock(message_id: str | int) -> asyncio.Lock:
    key = str(message_id)
    lock = _message_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _message_locks[key] = lock
    return lock


def get_emojis(c: Connection, starboard_id: int) -> list[str]:
    return [
        row[0]
        for row in c.execute(
            select(starboard_emojis.c.emoji)
            .where(starboard_emojis.c.starboard_id == starboard_id)
            .order_by(starboard_emojis.c.position, starboard_emojis.c.id)
        ).fetchall()
    ]


def load_starboard(c: Connection, starboard_id: int) -> dict | None:
    row = c.execute(
        select(starboards).where(starboards.c.id == starboard_id)
    ).fetchone()
    if row is None:
        return None

    return {
        "id": row.id,
        "cid": row.cid,
        "min_count": row.min_count,
        "emojis": get_emojis(c, row.id),
    }


def load_guild_starboards(c: Connection, gid: str) -> list[dict]:
    rows = c.execute(
        select(starboards).where(starboards.c.gid == gid).order_by(starboards.c.id)
    ).fetchall()
    if not rows:
        return []

    ids = [row.id for row in rows]
    emoji_rows = c.execute(
        select(starboard_emojis)
        .where(starboard_emojis.c.starboard_id.in_(ids))
        .order_by(starboard_emojis.c.position, starboard_emojis.c.id)
    ).fetchall()

    by_starboard: dict[int, list[str]] = {row.id: [] for row in rows}
    for row in emoji_rows:
        by_starboard[row.starboard_id].append(row.emoji)

    return [
        {
            "id": row.id,
            "cid": row.cid,
            "min_count": row.min_count,
            "emojis": by_starboard[row.id],
        }
        for row in rows
    ]


def _get_guild_channel(guild, channel_id):
    channel = guild.get_channel(int(channel_id))
    if channel is not None:
        return channel

    get_thread = getattr(guild, "get_thread", None)
    if get_thread is not None:
        return get_thread(int(channel_id))

    return None


async def _fetch_message(
    bot: Bot, guild, channel_id, message_id
) -> Message:
    channel = _get_guild_channel(guild, channel_id)
    if channel is None:
        channel = await bot.fetch_channel(int(channel_id))

    return await channel.fetch_message(int(message_id))


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def build_starboard_embed(source: Message, count: int, emojis: list[str]) -> Embed:
    content = source.content or ""
    embed = Embed(
        description=_truncate(content, 4096) if content else None,
        color=Color.gold(),
        timestamp=source.created_at,
    )
    embed.set_author(
        name=source.author.display_name,
        icon_url=source.author.display_avatar.url,
    )

    attachments = list(source.attachments)
    images = [
        attachment
        for attachment in attachments
        if attachment.content_type is not None
        and attachment.content_type.startswith("image/")
    ]
    if images:
        embed.set_image(url=images[0].url)

    other_attachments = [attachment for attachment in attachments if attachment not in images]
    if other_attachments:
        links = "\n".join(
            f"[{_truncate(attachment.filename, 80)}]({attachment.url})"
            for attachment in other_attachments
        )
        embed.add_field(
            name="Attachments", value=_truncate(links, 1024), inline=False
        )

    if not content and not attachments:
        embed.description = "*No text content*"

    embed.add_field(
        name="Source",
        value=f"[Jump to message]({source.jump_url}) in {source.channel.mention}",
        inline=False,
    )

    if emojis:
        embed.add_field(
            name="Star reactions",
            value=_truncate(" ".join(emojis), 1024),
            inline=False,
        )

    embed.set_footer(
        text=f"{count} star{'s' if count != 1 else ''} • #{source.channel.name}"
    )

    return embed


async def count_stars(
    source: Message,
    copy: Message | None,
    allowed: set[str],
    author_id: int,
    bot_id: int,
) -> int:
    users: set[int] = set()

    messages = [(source, False)]
    if copy is not None:
        messages.append((copy, True))

    for message, skip_author in messages:
        for reaction in message.reactions:
            if normalize_emoji(reaction.emoji) not in allowed:
                continue

            async for user in reaction.users():
                if user.bot or user.id == bot_id:
                    continue
                if skip_author and user.id == author_id:
                    continue
                users.add(user.id)

    return len(users)


def _can_post(guild, channel) -> bool:
    permissions = channel.permissions_for(guild.me)
    return all(
        (
            permissions.view_channel,
            permissions.send_messages,
            permissions.embed_links,
            permissions.read_message_history,
        )
    )


def update_bot_permission(c: Connection, guild, channel) -> bool:
    permissions = channel.permissions_for(guild.me)
    ok = all(
        (
            permissions.view_channel,
            permissions.send_messages,
            permissions.embed_links,
            permissions.read_message_history,
            permissions.manage_messages,
        )
    )
    setting_starboard_bot_ok.set(c, guild.id, str(ok).lower())
    return ok


def update_bot_permission_if_possible(guild, channel) -> None:
    try:
        with engine.begin() as c:
            update_bot_permission(c, guild, channel)
    except Exception as e:
        akabot_logger.exception(f"Failed to sync starboard permissions: {e}")


async def sync_all_bot_permissions(bot: Bot) -> None:
    try:
        with engine.begin() as c:
            rows = c.execute(
                select(starboards.c.gid, starboards.c.cid)
            ).fetchall()
    except Exception as e:
        akabot_logger.exception(f"Failed to load starboards for permission sync: {e}")
        return

    for gid, cid in rows:
        guild = bot.get_guild(int(gid))
        if guild is None:
            continue

        channel = _get_guild_channel(guild, cid)
        if channel is None:
            continue

        update_bot_permission_if_possible(guild, channel)


def _delete_entry(entry_id: int) -> None:
    with engine.begin() as c:
        c.execute(
            delete(starboard_messages).where(starboard_messages.c.id == entry_id)
        )


async def _delete_message(message: Message) -> bool:
    try:
        await message.delete()
        return True
    except NotFound:
        return True
    except (Forbidden, HTTPException) as e:
        akabot_logger.warning(
            f"Failed to delete starboard message {message.id}: {e}"
        )
        return False


async def _delete_copy_for_entry(bot: Bot, guild, entry) -> None:
    channel = _get_guild_channel(guild, entry.starboard_cid)
    if channel is None:
        try:
            channel = await bot.fetch_channel(int(entry.starboard_cid))
        except (NotFound, Forbidden, HTTPException):
            channel = None

    if channel is not None:
        try:
            message = await channel.fetch_message(int(entry.starboard_mid))
        except NotFound:
            message = None
        except (Forbidden, HTTPException) as e:
            akabot_logger.warning(
                f"Failed to fetch starboard message {entry.starboard_mid}: {e}"
            )
            message = None

        if message is not None:
            await _delete_message(message)

    _delete_entry(entry.id)


async def _remove_below_threshold(entry, copy: Message) -> None:
    deleted = await _delete_message(copy)
    if deleted:
        _delete_entry(entry.id)
    else:
        akabot_logger.warning(
            f"Keeping starboard entry {entry.id} because message "
            f"{entry.starboard_mid} could not be deleted"
        )


async def _create_copy(
    bot: Bot, guild, config: dict, source: Message, count: int
) -> None:
    channel = _get_guild_channel(guild, config["cid"])
    if channel is None:
        raise ValueError(f"Starboard channel {config['cid']} not found")

    update_bot_permission_if_possible(guild, channel)

    if not _can_post(guild, channel):
        raise ValueError(
            f"Missing permissions to post in starboard channel {channel.name}"
        )

    embed = build_starboard_embed(source, count, config["emojis"])
    message = await channel.send(embed=embed)

    try:
        with engine.begin() as c:
            c.execute(
                insert(starboard_messages).values(
                    starboard_id=config["id"],
                    gid=str(guild.id),
                    cid=str(source.channel.id),
                    mid=str(source.id),
                    starboard_cid=str(channel.id),
                    starboard_mid=str(message.id),
                    author_id=str(source.author.id),
                    created_at=datetime.datetime.now(datetime.UTC),
                )
            )
    except Exception:
        try:
            await message.delete()
        except Exception:
            pass
        raise


async def _update_copy(
    copy: Message, source: Message, count: int, emojis: list[str]
) -> bool:
    embed = build_starboard_embed(source, count, emojis)
    try:
        await copy.edit(embed=embed)
        return True
    except NotFound:
        return False


async def _handle_copy_reaction(bot: Bot, gid: str, entry, emoji_key: str | None) -> None:
    with engine.begin() as c:
        config = load_starboard(c, entry.starboard_id)

    if config is None:
        _delete_entry(entry.id)
        return

    allowed = {normalize_emoji(emoji) for emoji in config["emojis"]}
    if not allowed:
        return
    if emoji_key is not None and emoji_key not in allowed:
        return

    guild = bot.get_guild(int(gid))
    if guild is None:
        return

    try:
        source = await _fetch_message(bot, guild, entry.cid, entry.mid)
    except NotFound:
        await _delete_copy_for_entry(bot, guild, entry)
        return

    try:
        copy = await _fetch_message(
            bot, guild, entry.starboard_cid, entry.starboard_mid
        )
    except NotFound:
        _delete_entry(entry.id)
        return

    bot_id = bot.user.id if bot.user is not None else 0
    count = await count_stars(
        source, copy, allowed, int(entry.author_id), bot_id
    )

    if count >= config["min_count"]:
        updated = await _update_copy(copy, source, count, config["emojis"])
        if not updated:
            _delete_entry(entry.id)
    else:
        await _remove_below_threshold(entry, copy)


async def _handle_source_reaction(
    bot: Bot,
    gid: str,
    channel_id: int,
    message_id: str,
    source_entries: list,
    emoji_key: str | None,
) -> None:
    guild = bot.get_guild(int(gid))
    if guild is None:
        return

    if not source_entries:
        with engine.begin() as c:
            in_starboard = c.execute(
                select(starboards.c.id).where(
                    (starboards.c.gid == gid)
                    & (starboards.c.cid == str(channel_id))
                )
            ).fetchone()

        if in_starboard is not None:
            return

    with engine.begin() as c:
        configs = load_guild_starboards(c, gid)

    matching_configs = []
    for config in configs:
        allowed = {normalize_emoji(emoji) for emoji in config["emojis"]}
        if not allowed:
            continue
        if emoji_key is not None and emoji_key not in allowed:
            continue
        matching_configs.append((config, allowed))

    if not matching_configs:
        return

    try:
        source = await _fetch_message(bot, guild, channel_id, message_id)
    except NotFound:
        for entry in source_entries:
            await _delete_copy_for_entry(bot, guild, entry)
        return

    if source.author.bot:
        return

    entries_by_config = {
        entry.starboard_id: entry for entry in source_entries
    }
    bot_id = bot.user.id if bot.user is not None else 0

    for config, allowed in matching_configs:
        entry = entries_by_config.get(config["id"])
        if entry is None:
            count = await count_stars(
                source, None, allowed, source.author.id, bot_id
            )
            if count >= config["min_count"]:
                await _create_copy(bot, guild, config, source, count)
            continue

        try:
            copy = await _fetch_message(
                bot, guild, entry.starboard_cid, entry.starboard_mid
            )
        except NotFound:
            _delete_entry(entry.id)
            continue

        count = await count_stars(
            source, copy, allowed, int(entry.author_id), bot_id
        )

        if count >= config["min_count"]:
            updated = await _update_copy(copy, source, count, config["emojis"])
            if not updated:
                _delete_entry(entry.id)
        else:
            await _remove_below_threshold(entry, copy)


async def handle_reaction_event(bot: Bot, payload, emoji=None) -> None:
    if payload.guild_id is None:
        return

    bot_id = bot.user.id if bot.user is not None else 0
    user_id = getattr(payload, "user_id", None)
    if user_id is not None:
        if user_id == bot_id:
            return
        user = bot.get_user(user_id)
        if user is not None and user.bot:
            return

    gid = str(payload.guild_id)
    message_id = str(payload.message_id)
    emoji_key = normalize_emoji(emoji) if emoji is not None else None

    with engine.begin() as c:
        copy_entry = c.execute(
            select(starboard_messages).where(
                (starboard_messages.c.gid == gid)
                & (starboard_messages.c.starboard_mid == message_id)
            )
        ).fetchone()

        source_entries = []
        if copy_entry is None:
            source_entries = c.execute(
                select(starboard_messages).where(
                    (starboard_messages.c.gid == gid)
                    & (starboard_messages.c.mid == message_id)
                )
            ).fetchall()

    lock_key = copy_entry.mid if copy_entry is not None else message_id
    async with _message_lock(lock_key):
        if copy_entry is not None:
            await _handle_copy_reaction(bot, gid, copy_entry, emoji_key)
        else:
            await _handle_source_reaction(
                bot,
                gid,
                payload.channel_id,
                message_id,
                source_entries,
                emoji_key,
            )


async def handle_message_delete(bot: Bot, guild_id: int, message_id: int) -> None:
    guild = bot.get_guild(int(guild_id))
    if guild is None:
        return

    gid = str(guild_id)
    mid = str(message_id)

    with engine.begin() as c:
        copy_entries = c.execute(
            select(starboard_messages).where(
                (starboard_messages.c.gid == gid)
                & (starboard_messages.c.starboard_mid == mid)
            )
        ).fetchall()
        source_entries = c.execute(
            select(starboard_messages).where(
                (starboard_messages.c.gid == gid)
                & (starboard_messages.c.mid == mid)
            )
        ).fetchall()

    for entry in copy_entries:
        _delete_entry(entry.id)

    for entry in source_entries:
        await _delete_copy_for_entry(bot, guild, entry)


async def handle_bulk_message_delete(
    bot: Bot, guild_id: int, message_ids: list[int]
) -> None:
    for message_id in message_ids:
        await handle_message_delete(bot, guild_id, message_id)


async def handle_message_edit(bot: Bot, guild_id: int, message_id: int) -> None:
    guild = bot.get_guild(int(guild_id))
    if guild is None:
        return

    gid = str(guild_id)
    mid = str(message_id)

    with engine.begin() as c:
        entries = c.execute(
            select(starboard_messages).where(
                (starboard_messages.c.gid == gid)
                & (starboard_messages.c.mid == mid)
            )
        ).fetchall()

    if not entries:
        return

    try:
        source = await _fetch_message(bot, guild, entries[0].cid, mid)
    except NotFound:
        return

    bot_id = bot.user.id if bot.user is not None else 0

    for entry in entries:
        with engine.begin() as c:
            config = load_starboard(c, entry.starboard_id)

        if config is None:
            _delete_entry(entry.id)
            continue

        allowed = {normalize_emoji(emoji) for emoji in config["emojis"]}
        if not allowed:
            continue

        try:
            copy = await _fetch_message(
                bot, guild, entry.starboard_cid, entry.starboard_mid
            )
        except NotFound:
            _delete_entry(entry.id)
            continue

        count = await count_stars(
            source, copy, allowed, int(entry.author_id), bot_id
        )
        if count >= config["min_count"]:
            updated = await _update_copy(copy, source, count, config["emojis"])
            if not updated:
                _delete_entry(entry.id)


async def handle_channel_delete(
    bot: Bot, guild_id: int, channel_id: int
) -> None:
    guild = bot.get_guild(int(guild_id))
    gid = str(guild_id)
    cid = str(channel_id)

    with engine.begin() as c:
        configs = c.execute(
            select(starboards).where(
                (starboards.c.gid == gid) & (starboards.c.cid == cid)
            )
        ).fetchall()
        config_ids = [row.id for row in configs]

        source_entries = c.execute(
            select(starboard_messages).where(
                (starboard_messages.c.gid == gid)
                & (starboard_messages.c.cid == cid)
            )
        ).fetchall()

        if config_ids:
            c.execute(
                delete(starboard_emojis).where(
                    starboard_emojis.c.starboard_id.in_(config_ids)
                )
            )
            c.execute(
                delete(starboard_messages).where(
                    starboard_messages.c.starboard_id.in_(config_ids)
                )
            )
            c.execute(delete(starboards).where(starboards.c.id.in_(config_ids)))

        c.execute(
            delete(starboard_messages).where(
                (starboard_messages.c.gid == gid)
                & (starboard_messages.c.starboard_cid == cid)
            )
        )

        if source_entries:
            c.execute(
                delete(starboard_messages).where(
                    starboard_messages.c.id.in_(
                        [entry.id for entry in source_entries]
                    )
                )
            )

    if guild is None:
        return

    for entry in source_entries:
        if entry.starboard_cid == cid:
            continue

        channel = _get_guild_channel(guild, entry.starboard_cid)
        if channel is None:
            continue

        try:
            message = await channel.fetch_message(int(entry.starboard_mid))
        except NotFound:
            continue
        except (Forbidden, HTTPException):
            continue

        await _delete_message(message)


@register_task("starboards_cleanup")
async def handle_cleanup(bot: Bot, data: dict) -> None:
    guild_id = data.get("gid")
    if not guild_id:
        return

    guild = bot.get_guild(int(guild_id))
    if guild is None:
        return

    for post in data.get("posts", []):
        try:
            cid = int(post["cid"])
            mid = int(post["mid"])
        except (KeyError, TypeError, ValueError):
            continue

        channel = _get_guild_channel(guild, cid)
        if channel is None:
            try:
                channel = await bot.fetch_channel(cid)
            except (NotFound, Forbidden, HTTPException):
                continue

        try:
            message = await channel.fetch_message(mid)
        except NotFound:
            continue
        except (Forbidden, HTTPException):
            continue

        if not await _delete_message(message):
            raise ValueError(f"Failed to delete starboard message {mid}")
