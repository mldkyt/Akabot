import datetime
import time
from dataclasses import dataclass
from datetime import timedelta

from discord import Embed, EmbedField, Member, Message

from database import engine
from utils.logs import send_message_to_log_channel
from utils.server_settings import ServerSetting, SettingType

setting_no_avatar = ServerSetting(
    name="Kick users with no avatar", setting_type=SettingType.NORMAL, default="false"
)

setting_minimum_age = ServerSetting(
    name="Minimum user age (days)", setting_type=SettingType.NORMAL, default="false"
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


@dataclass
class MediaPost:
    timestamp: float
    message: Message


mrbeast_media_posts: dict[int, dict[int, list[MediaPost]]] = {}


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

    with engine.begin() as c:
        if setting_mrbeast_scam.get(c, message.guild.id) != "true":
            return
        action = setting_mrbeast_action.get(c, message.guild.id)

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

    reason = (
        f"MrBeast scam: posting {trigger_count} media into {len(channels)} "
        "channels within 10 seconds"
    )

    if action == "timeout":
        await member.timeout_for(timedelta(seconds=3600), reason=reason)
        action_name = "Timeout"
    elif action == "kick":
        await member.kick(reason=reason)
        action_name = "Kick"
    elif action == "ban":
        await member.ban(reason=reason, delete_message_seconds=0)
        action_name = "Ban"
    else:
        await member.timeout_for(timedelta(seconds=3600), reason=reason)
        action_name = "Timeout"

    with engine.begin() as c:
        await send_message_to_log_channel(
            c,
            message.guild,
            "anti_raid_mrbeast",
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
