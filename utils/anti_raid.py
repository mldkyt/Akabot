import datetime
import hashlib
import re
import time
from dataclasses import dataclass
from datetime import timedelta

from discord import Embed, EmbedField, Member, Message

from database import engine
from utils.logs import send_message_to_log_channel
from utils.server_settings import ServerSetting, SettingType

INVITE_RE = re.compile(r"discord(?:app)?\.com/invite/\w+|discord\.gg/\w+", re.IGNORECASE)

_EMOJI_RANGES = (
    "\U0001F600-\U0001F64F",
    "\U0001F300-\U0001F5FF",
    "\U0001F680-\U0001F6FF",
    "\U0001F1E0-\U0001F1FF",
    "\U0001F900-\U0001F9FF",
    "\U0001FA00-\U0001FA6F",
    "\U0001FA70-\U0001FAFF",
    "\U00002702-\U000027B0",
    "\U0000FE00-\U0000FE0F",
    "\U0000200D",
    "\U00002640-\U00002642",
    "\U00002600-\U000026FF",
    "\U0000231A-\U0000231B",
    "\U00002934-\U00002935",
    "\U000025AA-\U000025AB",
    "\U000025FB-\U000025FE",
)
_EMOJI_RE = re.compile("[" + "".join(_EMOJI_RANGES) + "]")


def _count_emojis(text: str) -> int:
    return len(_EMOJI_RE.findall(text))

DEFAULT_DM_MESSAGE = "You have been flagged by {guild}'s anti raid system: {reason}"
DEFAULT_MR_BEAST_REASON = (
    "MrBeast scam: posting {count} media into {channels} channels within 10 seconds"
)
DEFAULT_FLOOD_REASON = "Message flood: {count} messages in {window} seconds"
DEFAULT_DUPLICATE_REASON = (
    "Duplicate message spam: same message sent {count} times in {window} seconds"
)
DEFAULT_MENTIONS_REASON = "Mass mentions: {count} mentions in a single message"
DEFAULT_INVITE_REASON = (
    "Invite/link spam: {count} messages with links in {window} seconds"
)
DEFAULT_CAPS_REASON = "Caps flood: {percentage}% uppercase in {characters} characters"
DEFAULT_EMOJI_REASON = "Emoji flood: {count} emojis in {window} seconds"
DEFAULT_STICKER_REASON = "Sticker flood: {count} stickers in {window} seconds"
DEFAULT_JOINBURST_REASON = "Join burst: {count} members joined in {window} seconds"

setting_no_avatar = ServerSetting(
    name="Kick users with no avatar", setting_type=SettingType.NORMAL, default="false"
)

setting_minimum_age = ServerSetting(
    name="Minimum user age (days)", setting_type=SettingType.NORMAL, default="0"
)

setting_mrbeast_scam = ServerSetting(
    name="MrBeast scam detection",
    setting_type=SettingType.NORMAL,
    default="false",
)

setting_mrbeast_action = ServerSetting(
    name="MrBeast scam detection action",
    setting_type=SettingType.NORMAL,
    default="timeout",
)

setting_mrbeast_dm = ServerSetting(
    name="MrBeast scam detection dm",
    setting_type=SettingType.NORMAL,
    default="false",
)

setting_mrbeast_timeout = ServerSetting(
    name="MrBeast scam detection timeout",
    setting_type=SettingType.NORMAL,
    default="3600",
)

setting_mrbeast_dm_message = ServerSetting(
    name="MrBeast scam detection dm message",
    setting_type=SettingType.NORMAL,
    default=DEFAULT_DM_MESSAGE,
)

setting_mrbeast_reason = ServerSetting(
    name="MrBeast scam detection reason",
    setting_type=SettingType.NORMAL,
    default=DEFAULT_MR_BEAST_REASON,
)

setting_flood_enabled = ServerSetting(
    name="Anti Raid: Flood enabled", setting_type=SettingType.NORMAL, default="false"
)

setting_flood_action = ServerSetting(
    name="Anti Raid: Flood action", setting_type=SettingType.NORMAL, default="timeout"
)

setting_flood_dm = ServerSetting(
    name="Anti Raid: Flood dm", setting_type=SettingType.NORMAL, default="false"
)

setting_flood_timeout = ServerSetting(
    name="Anti Raid: Flood timeout", setting_type=SettingType.NORMAL, default="3600"
)

setting_flood_dm_message = ServerSetting(
    name="Anti Raid: Flood dm message",
    setting_type=SettingType.NORMAL,
    default=DEFAULT_DM_MESSAGE,
)

setting_flood_reason = ServerSetting(
    name="Anti Raid: Flood reason",
    setting_type=SettingType.NORMAL,
    default=DEFAULT_FLOOD_REASON,
)

setting_flood_count = ServerSetting(
    name="Anti Raid: Flood count", setting_type=SettingType.NORMAL, default="10"
)

setting_flood_window = ServerSetting(
    name="Anti Raid: Flood window", setting_type=SettingType.NORMAL, default="5"
)

setting_duplicate_enabled = ServerSetting(
    name="Anti Raid: Duplicate enabled", setting_type=SettingType.NORMAL, default="false"
)

setting_duplicate_action = ServerSetting(
    name="Anti Raid: Duplicate action", setting_type=SettingType.NORMAL, default="timeout"
)

setting_duplicate_dm = ServerSetting(
    name="Anti Raid: Duplicate dm", setting_type=SettingType.NORMAL, default="false"
)

setting_duplicate_timeout = ServerSetting(
    name="Anti Raid: Duplicate timeout", setting_type=SettingType.NORMAL, default="3600"
)

setting_duplicate_dm_message = ServerSetting(
    name="Anti Raid: Duplicate dm message",
    setting_type=SettingType.NORMAL,
    default=DEFAULT_DM_MESSAGE,
)

setting_duplicate_reason = ServerSetting(
    name="Anti Raid: Duplicate reason",
    setting_type=SettingType.NORMAL,
    default=DEFAULT_DUPLICATE_REASON,
)

setting_duplicate_count = ServerSetting(
    name="Anti Raid: Duplicate count", setting_type=SettingType.NORMAL, default="5"
)

setting_duplicate_window = ServerSetting(
    name="Anti Raid: Duplicate window", setting_type=SettingType.NORMAL, default="30"
)

setting_mentions_enabled = ServerSetting(
    name="Anti Raid: Mentions enabled", setting_type=SettingType.NORMAL, default="false"
)

setting_mentions_action = ServerSetting(
    name="Anti Raid: Mentions action", setting_type=SettingType.NORMAL, default="timeout"
)

setting_mentions_dm = ServerSetting(
    name="Anti Raid: Mentions dm", setting_type=SettingType.NORMAL, default="false"
)

setting_mentions_timeout = ServerSetting(
    name="Anti Raid: Mentions timeout", setting_type=SettingType.NORMAL, default="3600"
)

setting_mentions_dm_message = ServerSetting(
    name="Anti Raid: Mentions dm message",
    setting_type=SettingType.NORMAL,
    default=DEFAULT_DM_MESSAGE,
)

setting_mentions_reason = ServerSetting(
    name="Anti Raid: Mentions reason",
    setting_type=SettingType.NORMAL,
    default=DEFAULT_MENTIONS_REASON,
)

setting_mentions_count = ServerSetting(
    name="Anti Raid: Mentions count", setting_type=SettingType.NORMAL, default="5"
)

setting_invite_enabled = ServerSetting(
    name="Anti Raid: Invite enabled", setting_type=SettingType.NORMAL, default="false"
)

setting_invite_action = ServerSetting(
    name="Anti Raid: Invite action", setting_type=SettingType.NORMAL, default="timeout"
)

setting_invite_dm = ServerSetting(
    name="Anti Raid: Invite dm", setting_type=SettingType.NORMAL, default="false"
)

setting_invite_timeout = ServerSetting(
    name="Anti Raid: Invite timeout", setting_type=SettingType.NORMAL, default="3600"
)

setting_invite_dm_message = ServerSetting(
    name="Anti Raid: Invite dm message",
    setting_type=SettingType.NORMAL,
    default=DEFAULT_DM_MESSAGE,
)

setting_invite_reason = ServerSetting(
    name="Anti Raid: Invite reason",
    setting_type=SettingType.NORMAL,
    default=DEFAULT_INVITE_REASON,
)

setting_invite_count = ServerSetting(
    name="Anti Raid: Invite count", setting_type=SettingType.NORMAL, default="3"
)

setting_invite_window = ServerSetting(
    name="Anti Raid: Invite window", setting_type=SettingType.NORMAL, default="60"
)

setting_caps_enabled = ServerSetting(
    name="Anti Raid: Caps enabled", setting_type=SettingType.NORMAL, default="false"
)

setting_caps_action = ServerSetting(
    name="Anti Raid: Caps action", setting_type=SettingType.NORMAL, default="timeout"
)

setting_caps_dm = ServerSetting(
    name="Anti Raid: Caps dm", setting_type=SettingType.NORMAL, default="false"
)

setting_caps_timeout = ServerSetting(
    name="Anti Raid: Caps timeout", setting_type=SettingType.NORMAL, default="3600"
)

setting_caps_dm_message = ServerSetting(
    name="Anti Raid: Caps dm message",
    setting_type=SettingType.NORMAL,
    default=DEFAULT_DM_MESSAGE,
)

setting_caps_reason = ServerSetting(
    name="Anti Raid: Caps reason",
    setting_type=SettingType.NORMAL,
    default=DEFAULT_CAPS_REASON,
)

setting_caps_percentage = ServerSetting(
    name="Anti Raid: Caps percentage", setting_type=SettingType.NORMAL, default="80"
)

setting_caps_min_length = ServerSetting(
    name="Anti Raid: Caps min length", setting_type=SettingType.NORMAL, default="10"
)

setting_emoji_enabled = ServerSetting(
    name="Anti Raid: Emoji enabled", setting_type=SettingType.NORMAL, default="false"
)

setting_emoji_action = ServerSetting(
    name="Anti Raid: Emoji action", setting_type=SettingType.NORMAL, default="timeout"
)

setting_emoji_dm = ServerSetting(
    name="Anti Raid: Emoji dm", setting_type=SettingType.NORMAL, default="false"
)

setting_emoji_timeout = ServerSetting(
    name="Anti Raid: Emoji timeout", setting_type=SettingType.NORMAL, default="3600"
)

setting_emoji_dm_message = ServerSetting(
    name="Anti Raid: Emoji dm message",
    setting_type=SettingType.NORMAL,
    default=DEFAULT_DM_MESSAGE,
)

setting_emoji_reason = ServerSetting(
    name="Anti Raid: Emoji reason",
    setting_type=SettingType.NORMAL,
    default=DEFAULT_EMOJI_REASON,
)

setting_emoji_count = ServerSetting(
    name="Anti Raid: Emoji count", setting_type=SettingType.NORMAL, default="10"
)

setting_emoji_window = ServerSetting(
    name="Anti Raid: Emoji window", setting_type=SettingType.NORMAL, default="5"
)

setting_sticker_enabled = ServerSetting(
    name="Anti Raid: Sticker enabled", setting_type=SettingType.NORMAL, default="false"
)

setting_sticker_action = ServerSetting(
    name="Anti Raid: Sticker action", setting_type=SettingType.NORMAL, default="timeout"
)

setting_sticker_dm = ServerSetting(
    name="Anti Raid: Sticker dm", setting_type=SettingType.NORMAL, default="false"
)

setting_sticker_timeout = ServerSetting(
    name="Anti Raid: Sticker timeout", setting_type=SettingType.NORMAL, default="3600"
)

setting_sticker_dm_message = ServerSetting(
    name="Anti Raid: Sticker dm message",
    setting_type=SettingType.NORMAL,
    default=DEFAULT_DM_MESSAGE,
)

setting_sticker_reason = ServerSetting(
    name="Anti Raid: Sticker reason",
    setting_type=SettingType.NORMAL,
    default=DEFAULT_STICKER_REASON,
)

setting_sticker_count = ServerSetting(
    name="Anti Raid: Sticker count", setting_type=SettingType.NORMAL, default="5"
)

setting_sticker_window = ServerSetting(
    name="Anti Raid: Sticker window", setting_type=SettingType.NORMAL, default="10"
)

setting_joinburst_enabled = ServerSetting(
    name="Anti Raid: Join burst enabled", setting_type=SettingType.NORMAL, default="false"
)

setting_joinburst_action = ServerSetting(
    name="Anti Raid: Join burst action", setting_type=SettingType.NORMAL, default="ban"
)

setting_joinburst_dm = ServerSetting(
    name="Anti Raid: Join burst dm", setting_type=SettingType.NORMAL, default="false"
)

setting_joinburst_timeout = ServerSetting(
    name="Anti Raid: Join burst timeout", setting_type=SettingType.NORMAL, default="3600"
)

setting_joinburst_dm_message = ServerSetting(
    name="Anti Raid: Join burst dm message",
    setting_type=SettingType.NORMAL,
    default=DEFAULT_DM_MESSAGE,
)

setting_joinburst_reason = ServerSetting(
    name="Anti Raid: Join burst reason",
    setting_type=SettingType.NORMAL,
    default=DEFAULT_JOINBURST_REASON,
)

setting_joinburst_count = ServerSetting(
    name="Anti Raid: Join burst count", setting_type=SettingType.NORMAL, default="10"
)

setting_joinburst_window = ServerSetting(
    name="Anti Raid: Join burst window", setting_type=SettingType.NORMAL, default="30"
)


@dataclass
class MediaPost:
    timestamp: float
    message: Message


mrbeast_media_posts: dict[int, dict[int, list[MediaPost]]] = {}

flood_messages: dict[int, dict[int, list[float]]] = {}

duplicate_messages: dict[int, dict[int, list[tuple[float, str]]]] = {}

invite_spam_messages: dict[int, dict[int, list[float]]] = {}

emoji_flood_messages: dict[int, dict[int, list[float]]] = {}

sticker_flood_messages: dict[int, dict[int, list[float]]] = {}

join_burst_joins: dict[int, list[tuple[float, int]]] = {}


ACTION_NAMES = {
    "timeout": "Timeout",
    "kick": "Kick",
    "ban": "Ban",
    "log": "Log",
}


async def perform_action(member: Member, action: str, reason: str, timeout: int = 3600) -> str:
    if action == "log":
        return "Log"
    elif action == "timeout":
        await member.timeout_for(timedelta(seconds=timeout), reason=reason)
    elif action == "kick":
        await member.kick(reason=reason)
    elif action == "ban":
        await member.ban(reason=reason, delete_message_seconds=0)
    else:
        await member.timeout_for(timedelta(seconds=timeout), reason=reason)
    return ACTION_NAMES.get(action, "Timeout")


async def send_anti_raid_log(
    c, guild, member: Member, action_name: str, reason: str, extra_fields=None
):
    fields = [
        EmbedField(
            name="Member",
            value=f"{member.display_name} ({member.name}; {member.id})",
        ),
        EmbedField(name="Action", value=action_name),
        EmbedField(name="Reason", value=reason),
    ]
    if extra_fields:
        fields.extend(extra_fields)

    await send_message_to_log_channel(
        c,
        guild,
        "anti_raid",
        Embed(
            title="Anti Raid",
            fields=fields,
        ),
    )


async def send_anti_raid_dm(member: Member, message: str):
    try:
        await member.send(content=message)
    except Exception:
        pass


def _format_template(template: str, member: Member, values: dict[str, str]) -> str:
    replacements = {
        "{guild}": member.guild.name,
        "{username}": member.name,
        "{display_name}": member.display_name,
        "{member}": member.display_name,
    }
    replacements.update(values)
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template


def _prune_window(items: list[float], window: float, now: float) -> list[float]:
    return [t for t in items if now - t <= window]


async def verify_member(member: Member):
    with engine.begin() as c:
        kick_no_avatar = setting_no_avatar.get(c, member.guild.id) == "true"
        kick_minimum_age = int(setting_minimum_age.get(c, member.guild.id))

    if kick_no_avatar and member.avatar is None:
        await member.kick(reason="Anti Raid: User has no avatar")
        return

    if kick_minimum_age == 0:
        return

    account_age = (
        datetime.datetime.now() - member.created_at.replace(tzinfo=None)
    ).days
    if account_age < kick_minimum_age:
        await member.kick(
            reason=f"Anti Raid: User is below minimum account age ({account_age} < {kick_minimum_age})"
        )


async def handle_mrbeast_scam(message: Message):
    if message.guild is None:
        return

    if not message.attachments:
        return

    with engine.begin() as c:
        if setting_mrbeast_scam.get(c, message.guild.id) != "true":
            return
        action = setting_mrbeast_action.get(c, message.guild.id)
        dm = setting_mrbeast_dm.get(c, message.guild.id) == "true"
        timeout = int(setting_mrbeast_timeout.get(c, message.guild.id))
        dm_template = (
            setting_mrbeast_dm_message.get(c, message.guild.id) or DEFAULT_DM_MESSAGE
        )
        reason_template = (
            setting_mrbeast_reason.get(c, message.guild.id) or DEFAULT_MR_BEAST_REASON
        )

    member = message.author
    now = time.time()

    guild_posts = mrbeast_media_posts.setdefault(message.guild.id, {})
    member_posts = guild_posts.setdefault(member.id, [])
    member_posts.append(MediaPost(timestamp=now, message=message))

    member_posts = [
        post for post in member_posts if now - post.timestamp <= 60
    ]
    guild_posts[member.id] = member_posts

    if len(member_posts) < 3:
        return

    media_counts: dict[int, int] = {}
    for post in member_posts:
        media_counts[post.message.channel.id] = (
            media_counts.get(post.message.channel.id, 0) + len(post.message.attachments)
        )

    trigger_count = None
    for count in sorted(media_counts.values(), reverse=True):
        if count > 0 and sum(1 for v in media_counts.values() if v == count) >= 3:
            trigger_count = count
            break

    if trigger_count is None:
        return

    scam_messages = [post.message for post in member_posts]
    channels = sorted({message.channel.id for message in scam_messages})

    values = {"{count}": str(trigger_count), "{channels}": str(len(channels))}
    reason = _format_template(reason_template, member, values)

    if dm:
        await send_anti_raid_dm(
            member, _format_template(dm_template, member, {**values, "{reason}": reason})
        )

    action_name = await perform_action(member, action, reason, timeout)

    with engine.begin() as c:
        await send_message_to_log_channel(
            c,
            message.guild,
            "anti_raid",
            Embed(
                title="MrBeast Scam Detection",
                description="Akabot detected a member posting the same media across multiple channels",
                fields=[
                    EmbedField(
                        name="Member",
                        value=f"{member.display_name} ({member.name}; {member.id})",
                    ),
                    EmbedField(name="Action", value=action_name),
                    EmbedField(
                        name="Channels",
                        value=", ".join(f"<#{channel}>" for channel in channels),
                    ),
                    EmbedField(name="Reason", value=reason),
                ],
            ),
        )

    for scam_message in scam_messages:
        try:
            await scam_message.delete()
        except Exception:
            pass

    guild_posts.pop(member.id, None)


async def handle_flood(message: Message):
    with engine.begin() as c:
        if setting_flood_enabled.get(c, message.guild.id) != "true":
            return
        action = setting_flood_action.get(c, message.guild.id)
        dm = setting_flood_dm.get(c, message.guild.id) == "true"
        timeout = int(setting_flood_timeout.get(c, message.guild.id))
        dm_template = (
            setting_flood_dm_message.get(c, message.guild.id) or DEFAULT_DM_MESSAGE
        )
        reason_template = (
            setting_flood_reason.get(c, message.guild.id) or DEFAULT_FLOOD_REASON
        )
        threshold = int(setting_flood_count.get(c, message.guild.id))
        window = int(setting_flood_window.get(c, message.guild.id))

    if threshold == 0 or window == 0:
        return

    member = message.author
    now = time.time()

    guild_msgs = flood_messages.setdefault(message.guild.id, {})
    member_msgs = guild_msgs.setdefault(member.id, [])
    member_msgs.append(now)

    member_msgs = _prune_window(member_msgs, window, now)
    guild_msgs[member.id] = member_msgs

    if len(member_msgs) < threshold:
        return

    values = {"{count}": str(len(member_msgs)), "{window}": str(window)}
    reason = _format_template(reason_template, member, values)

    if dm:
        await send_anti_raid_dm(
            member, _format_template(dm_template, member, {**values, "{reason}": reason})
        )

    action_name = await perform_action(member, action, reason, timeout)

    with engine.begin() as c:
        await send_anti_raid_log(
            c, message.guild, member, action_name, reason,
        )

    guild_msgs.pop(member.id, None)


async def handle_duplicate(message: Message):
    with engine.begin() as c:
        if setting_duplicate_enabled.get(c, message.guild.id) != "true":
            return
        action = setting_duplicate_action.get(c, message.guild.id)
        dm = setting_duplicate_dm.get(c, message.guild.id) == "true"
        timeout = int(setting_duplicate_timeout.get(c, message.guild.id))
        dm_template = (
            setting_duplicate_dm_message.get(c, message.guild.id) or DEFAULT_DM_MESSAGE
        )
        reason_template = (
            setting_duplicate_reason.get(c, message.guild.id) or DEFAULT_DUPLICATE_REASON
        )
        threshold = int(setting_duplicate_count.get(c, message.guild.id))
        window = int(setting_duplicate_window.get(c, message.guild.id))

    if threshold == 0 or window == 0:
        return

    member = message.author
    now = time.time()

    if not message.content:
        return

    content_hash = hashlib.md5(message.content.encode()).hexdigest()

    guild_msgs = duplicate_messages.setdefault(message.guild.id, {})
    member_msgs = guild_msgs.setdefault(member.id, [])
    member_msgs.append((now, content_hash))

    member_msgs = [(t, h) for t, h in member_msgs if now - t <= window]
    guild_msgs[member.id] = member_msgs

    same_count = sum(1 for _, h in member_msgs if h == content_hash)
    if same_count < threshold:
        return

    values = {"{count}": str(same_count), "{window}": str(window)}
    reason = _format_template(reason_template, member, values)

    if dm:
        await send_anti_raid_dm(
            member, _format_template(dm_template, member, {**values, "{reason}": reason})
        )

    action_name = await perform_action(member, action, reason, timeout)

    with engine.begin() as c:
        await send_anti_raid_log(
            c, message.guild, member, action_name, reason,
        )

    guild_msgs.pop(member.id, None)


async def handle_mass_mentions(message: Message):
    with engine.begin() as c:
        if setting_mentions_enabled.get(c, message.guild.id) != "true":
            return
        action = setting_mentions_action.get(c, message.guild.id)
        dm = setting_mentions_dm.get(c, message.guild.id) == "true"
        timeout = int(setting_mentions_timeout.get(c, message.guild.id))
        dm_template = (
            setting_mentions_dm_message.get(c, message.guild.id) or DEFAULT_DM_MESSAGE
        )
        reason_template = (
            setting_mentions_reason.get(c, message.guild.id) or DEFAULT_MENTIONS_REASON
        )
        threshold = int(setting_mentions_count.get(c, message.guild.id))

    if threshold == 0:
        return

    mention_count = (
        len(message.mentions)
        + len(message.role_mentions)
        + (1 if message.mention_everyone else 0)
    )
    if mention_count < threshold:
        return

    member = message.author
    values = {"{count}": str(mention_count)}
    reason = _format_template(reason_template, member, values)

    if dm:
        await send_anti_raid_dm(
            member, _format_template(dm_template, member, {**values, "{reason}": reason})
        )

    action_name = await perform_action(member, action, reason, timeout)

    with engine.begin() as c:
        await send_anti_raid_log(
            c, message.guild, member, action_name, reason,
        )


async def handle_invite_spam(message: Message):
    with engine.begin() as c:
        if setting_invite_enabled.get(c, message.guild.id) != "true":
            return
        action = setting_invite_action.get(c, message.guild.id)
        dm = setting_invite_dm.get(c, message.guild.id) == "true"
        timeout = int(setting_invite_timeout.get(c, message.guild.id))
        dm_template = (
            setting_invite_dm_message.get(c, message.guild.id) or DEFAULT_DM_MESSAGE
        )
        reason_template = (
            setting_invite_reason.get(c, message.guild.id) or DEFAULT_INVITE_REASON
        )
        threshold = int(setting_invite_count.get(c, message.guild.id))
        window = int(setting_invite_window.get(c, message.guild.id))

    if threshold == 0 or window == 0:
        return

    member = message.author
    now = time.time()

    matches = INVITE_RE.findall(message.content)
    if not matches:
        return

    guild_msgs = invite_spam_messages.setdefault(message.guild.id, {})
    member_msgs = guild_msgs.setdefault(member.id, [])
    member_msgs.append(now)

    member_msgs = _prune_window(member_msgs, window, now)
    guild_msgs[member.id] = member_msgs

    if len(member_msgs) < threshold:
        return

    values = {"{count}": str(len(member_msgs)), "{window}": str(window)}
    reason = _format_template(reason_template, member, values)

    if dm:
        await send_anti_raid_dm(
            member, _format_template(dm_template, member, {**values, "{reason}": reason})
        )

    action_name = await perform_action(member, action, reason, timeout)

    with engine.begin() as c:
        await send_anti_raid_log(
            c, message.guild, member, action_name, reason,
        )

    guild_msgs.pop(member.id, None)


async def handle_caps(message: Message):
    with engine.begin() as c:
        if setting_caps_enabled.get(c, message.guild.id) != "true":
            return
        action = setting_caps_action.get(c, message.guild.id)
        dm = setting_caps_dm.get(c, message.guild.id) == "true"
        timeout = int(setting_caps_timeout.get(c, message.guild.id))
        dm_template = (
            setting_caps_dm_message.get(c, message.guild.id) or DEFAULT_DM_MESSAGE
        )
        reason_template = (
            setting_caps_reason.get(c, message.guild.id) or DEFAULT_CAPS_REASON
        )
        threshold = int(setting_caps_percentage.get(c, message.guild.id))
        min_length = int(setting_caps_min_length.get(c, message.guild.id))

    if threshold == 0:
        return

    text = message.content
    alpha_chars = [c for c in text if c.isalpha()]
    if len(alpha_chars) == 0 or len(alpha_chars) < min_length:
        return

    upper_count = sum(1 for c in alpha_chars if c.isupper())
    percentage = int((upper_count / len(alpha_chars)) * 100)

    if percentage < threshold:
        return

    member = message.author
    values = {
        "{percentage}": str(percentage),
        "{characters}": str(len(alpha_chars)),
    }
    reason = _format_template(reason_template, member, values)

    if dm:
        await send_anti_raid_dm(
            member, _format_template(dm_template, member, {**values, "{reason}": reason})
        )

    action_name = await perform_action(member, action, reason, timeout)

    with engine.begin() as c:
        await send_anti_raid_log(
            c, message.guild, member, action_name, reason,
        )


async def handle_emoji_flood(message: Message):
    with engine.begin() as c:
        if setting_emoji_enabled.get(c, message.guild.id) != "true":
            return
        action = setting_emoji_action.get(c, message.guild.id)
        dm = setting_emoji_dm.get(c, message.guild.id) == "true"
        timeout = int(setting_emoji_timeout.get(c, message.guild.id))
        dm_template = (
            setting_emoji_dm_message.get(c, message.guild.id) or DEFAULT_DM_MESSAGE
        )
        reason_template = (
            setting_emoji_reason.get(c, message.guild.id) or DEFAULT_EMOJI_REASON
        )
        threshold = int(setting_emoji_count.get(c, message.guild.id))
        window = int(setting_emoji_window.get(c, message.guild.id))

    if threshold == 0 or window == 0:
        return

    emoji_count = _count_emojis(message.content)
    if emoji_count == 0:
        return

    member = message.author
    now = time.time()

    guild_msgs = emoji_flood_messages.setdefault(message.guild.id, {})
    member_msgs = guild_msgs.setdefault(member.id, [])

    for _ in range(emoji_count):
        member_msgs.append(now)

    member_msgs = _prune_window(member_msgs, window, now)
    guild_msgs[member.id] = member_msgs

    if len(member_msgs) < threshold:
        return

    values = {"{count}": str(len(member_msgs)), "{window}": str(window)}
    reason = _format_template(reason_template, member, values)

    if dm:
        await send_anti_raid_dm(
            member, _format_template(dm_template, member, {**values, "{reason}": reason})
        )

    action_name = await perform_action(member, action, reason, timeout)

    with engine.begin() as c:
        await send_anti_raid_log(
            c, message.guild, member, action_name, reason,
        )

    guild_msgs.pop(member.id, None)


async def handle_sticker_flood(message: Message):
    if len(message.stickers) == 0:
        return

    with engine.begin() as c:
        if setting_sticker_enabled.get(c, message.guild.id) != "true":
            return
        action = setting_sticker_action.get(c, message.guild.id)
        dm = setting_sticker_dm.get(c, message.guild.id) == "true"
        timeout = int(setting_sticker_timeout.get(c, message.guild.id))
        dm_template = (
            setting_sticker_dm_message.get(c, message.guild.id) or DEFAULT_DM_MESSAGE
        )
        reason_template = (
            setting_sticker_reason.get(c, message.guild.id) or DEFAULT_STICKER_REASON
        )
        threshold = int(setting_sticker_count.get(c, message.guild.id))
        window = int(setting_sticker_window.get(c, message.guild.id))

    if threshold == 0 or window == 0:
        return

    member = message.author
    now = time.time()

    guild_msgs = sticker_flood_messages.setdefault(message.guild.id, {})
    member_msgs = guild_msgs.setdefault(member.id, [])
    member_msgs.append(now)

    member_msgs = _prune_window(member_msgs, window, now)
    guild_msgs[member.id] = member_msgs

    if len(member_msgs) < threshold:
        return

    values = {"{count}": str(len(member_msgs)), "{window}": str(window)}
    reason = _format_template(reason_template, member, values)

    if dm:
        await send_anti_raid_dm(
            member, _format_template(dm_template, member, {**values, "{reason}": reason})
        )

    action_name = await perform_action(member, action, reason, timeout)

    with engine.begin() as c:
        await send_anti_raid_log(
            c, message.guild, member, action_name, reason,
        )

    guild_msgs.pop(member.id, None)


async def handle_join_burst(member: Member):
    with engine.begin() as c:
        if setting_joinburst_enabled.get(c, member.guild.id) != "true":
            return
        action = setting_joinburst_action.get(c, member.guild.id)
        dm = setting_joinburst_dm.get(c, member.guild.id) == "true"
        timeout = int(setting_joinburst_timeout.get(c, member.guild.id))
        dm_template = (
            setting_joinburst_dm_message.get(c, member.guild.id) or DEFAULT_DM_MESSAGE
        )
        reason_template = (
            setting_joinburst_reason.get(c, member.guild.id) or DEFAULT_JOINBURST_REASON
        )
        threshold = int(setting_joinburst_count.get(c, member.guild.id))
        window = int(setting_joinburst_window.get(c, member.guild.id))

    if threshold == 0 or window == 0:
        return

    now = time.time()

    guild_joins = join_burst_joins.setdefault(member.guild.id, [])
    guild_joins[:] = [(t, member_id) for t, member_id in guild_joins if member_id != member.id]
    guild_joins.append((now, member.id))

    guild_joins[:] = [(t, member_id) for t, member_id in guild_joins if now - t <= window]

    if len(guild_joins) < threshold:
        return

    burst_members = []
    for _, member_id in guild_joins:
        burst_member = member.guild.get_member(member_id)
        if burst_member is not None and burst_member not in burst_members:
            burst_members.append(burst_member)

    values = {"{count}": str(len(guild_joins)), "{window}": str(window)}
    reason = _format_template(reason_template, member, values)

    action_name = "Log"
    for burst_member in burst_members:
        if dm:
            await send_anti_raid_dm(
                burst_member,
                _format_template(
                    dm_template, burst_member, {**values, "{reason}": reason}
                ),
            )
        action_name = await perform_action(burst_member, action, reason, timeout)

    with engine.begin() as c:
        await send_anti_raid_log(
            c,
            member.guild,
            member,
            action_name,
            reason,
            extra_fields=[
                EmbedField(
                    name="Members",
                    value=", ".join(
                        f"{m.display_name} ({m.name}; {m.id})" for m in burst_members
                    ),
                ),
            ],
        )