import datetime
import uuid

from discord import Member, Embed, EmbedFooter, Color
from sqlalchemy import Connection

from database import engine
from logger import akabot_logger
from utils.server_settings import ServerSetting, SettingType
# Welcome
welcome_channel = ServerSetting(
    name="Welcome channel",
    setting_type=SettingType.NORMAL,
    default="0"
)

welcome_grace_period_first = ServerSetting(
    name="Welcoming first grace period",
    setting_type=SettingType.NORMAL,
    default="5"
)

welcome_grace_period_second = ServerSetting(
    name="Welcoming second grace period",
    setting_type=SettingType.NORMAL,
    default="5"
)

welcome_message_title = ServerSetting(
    name="Welcome message title",
    setting_type=SettingType.NORMAL,
    default="Welcome %m!"
)

welcome_message_message = ServerSetting(
    name="Welcome message",
    setting_type=SettingType.NORMAL,
    default="Welcome %m to %s. Hope you enjoy your stay."
)

welcome_message_type = ServerSetting(
    name="Welcome message type",
    setting_type=SettingType.NORMAL,
    default="embed"
)

# Goodbye
goodbye_channel = ServerSetting(
    name="Goodbye channel",
    setting_type=SettingType.NORMAL,
    default="0"
)

goodbye_message_title = ServerSetting(
    name="Goodbye message title",
    setting_type=SettingType.NORMAL,
    default="Goodbye %u"
)

goodbye_message_message = ServerSetting(
    name="Goodbye message",
    setting_type=SettingType.NORMAL,
    default="%s will miss you."
)

goodbye_message_type = ServerSetting(
    name="Goodbye message type",
    setting_type=SettingType.NORMAL,
    default="embed"
)

grace_period_first = {}
grace_period_second = {}


def add_member_to_grace_period(c: Connection, member: Member):
    dur = int(welcome_grace_period_first.get(c, member.guild.id))

    grace_period_first[uuid.uuid4()]= {
        'member': member,
        'after': datetime.datetime.now() + datetime.timedelta(seconds=dur)
    }


async def send_welcome_message(c: Connection, member: Member):
    chan = welcome_channel.get(c, member.guild.id)
    if chan == "":
        return

    dur = int(welcome_grace_period_second.get(c, member.guild.id))
    msg_type = welcome_message_type.get(c, member.guild.id)
    title = welcome_message_title.get(c, member.guild.id)
    msg = welcome_message_message.get(c, member.guild.id)

    title = title.replace("%m", member.mention)
    title = title.replace("%u", member.name)
    title = title.replace("%U", member.display_name)
    title = title.replace("%s", member.guild.name)

    msg = msg.replace("%m", member.mention)
    msg = msg.replace("%u", member.name)
    msg = msg.replace("%U", member.display_name)
    msg = msg.replace("%s", member.guild.name)

    chan = await member.guild.fetch_channel(int(chan))
    if msg_type == "embed":
        message = await chan.send(embed=Embed(
            title=title,
            description=msg,
            color=Color.green(),
            footer=EmbedFooter(
                text="Akabot welcomes you too!"  # TODO: turn the "Akabot" to a link
            )
        ))
        grace_period_second[uuid.uuid4()] ={
            'message': message,
            'member': member,
            'after': datetime.datetime.now() + datetime.timedelta(minutes=dur)
        }
    elif msg_type == "text":
        message = await chan.send(msg + "\nAkabot welcomes you too!")  # TODO: turn the "Akabot" to a link
        grace_period_second[uuid.uuid4()] ={
            'message': message,
            'member': member,
            'after': datetime.datetime.now() + datetime.timedelta(minutes=dur)
        }
    else:
        akabot_logger.warning("Invalid message type %s when welcoming member!", msg_type)

async def send_goodbye_message(c: Connection, member: Member):
    # Check first grace list
    for k, v in grace_period_first.items():
        if v['member'].id == member.id:
            akabot_logger.debug("Not sending goodbye message for %s, member is in join grace period",
                                member.display_name)
            del grace_period_first[k]
            return

    # Check second grace list
    for k, v in grace_period_second.items():
        if v['member'].id == member.id:
            akabot_logger.debug("Deleting welcome message for %s", member.display_name)
            await v['message'].delete()
            akabot_logger.debug("Not sending goodbye message for %s, member is in second grace period",
                                member.display_name)

            del grace_period_second[k]
            return

    chan = goodbye_channel.get(c, member.guild.id)
    if chan == "":
        return

    msg_type = goodbye_message_type.get(c, member.guild.id)
    title = goodbye_message_title.get(c, member.guild.id)
    msg = goodbye_message_message.get(c, member.guild.id)

    title = title.replace("%m", member.mention)
    title = title.replace("%u", member.name)
    title = title.replace("%U", member.display_name)
    title = title.replace("%s", member.guild.name)

    msg = msg.replace("%m", member.mention)
    msg = msg.replace("%u", member.name)
    msg = msg.replace("%U", member.display_name)
    msg = msg.replace("%s", member.guild.name)

    chan = await member.guild.fetch_channel(int(chan))
    if msg_type == "embed":
        await chan.send(embed=Embed(
            title=title,
            description=msg,
            color=Color.red()
        ))
    elif msg_type == "text":
        await chan.send(msg)
    else:
        akabot_logger.warning("Invalid message type %s when saying goodbye to member!", msg_type)


async def handle_first_grace_period():
    discard_these = []
    global grace_period_first

    for k, v in grace_period_first.items():
        if v['after'] < datetime.datetime.now():
            akabot_logger.debug("Sending welcome message for %s", v['member'].display_name)
            discard_these.append(k)
            with engine.begin() as c:
                try:
                    await send_welcome_message(c, v['member'])
                except Exception:
                    akabot_logger.exception("Failed to send welcome message")

    for i in discard_these:
        del grace_period_first[i]


def handle_second_grace_period():
    discard_these = []
    global grace_period_second

    for k, v in grace_period_second.items():
        if v['after'] < datetime.datetime.now():
            akabot_logger.debug("Discarding second grace period for %s", v['member'].display_name)
            discard_these.append(k)

    for i in discard_these:
        del grace_period_second[i]


async def handle_timed_events():
    await handle_first_grace_period()
    handle_second_grace_period()
