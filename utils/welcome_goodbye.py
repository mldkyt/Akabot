import datetime
import uuid

from discord import Member, Embed, EmbedFooter, Color
from sqlalchemy import Connection

from database import engine
from logger import nekona_logger
from utils.server_settings import ServerSetting, SettingType, setting_to_text_channel, \
    setting_simple_string, setting_number_within_range

# Welcome
welcome_channel = ServerSetting(
    name="Welcome channel",
    description="Set a channel to send welcome messages into.",
    setting_type=SettingType.NORMAL,
    normal_processor=setting_to_text_channel,
    normal_view=setting_simple_string("Channel for welcoming new members is set to <#%s>"),
    normal_response=setting_simple_string("Channel for welcoming new members was set to <#%s>"),
    default="0"
)

welcome_grace_period_first = ServerSetting(
    name="Welcoming first grace period",
    description="The number of seconds between a member join and the welcome message being sent. This can be used to not welcome raiders (if they get kicked quickly enough).",
    setting_type=SettingType.NORMAL,
    normal_processor=setting_number_within_range(0, 120),
    normal_view=setting_simple_string("First grace period (before welcome message is sent) is %s seconds"),
    normal_response=setting_simple_string("First grace period (before welcome message is sent) was set to %s seconds"),
    default="5"
)

welcome_grace_period_second = ServerSetting(
    name="Welcoming second grace period",
    description="The number of minutes between the welcome message sent and it persisting when the member leaves. When it persists, a goodbye message is sent instead when the member leaves. When a member joins the server for a short period of time, this will unclog the goodbye channel.",
    setting_type=SettingType.NORMAL,
    normal_processor=setting_number_within_range(0, 30),
    normal_view=setting_simple_string("Second grace period (after welcome message is sent) is %s minutes"),
    normal_response=setting_simple_string("Second grace period (after welcome message is sent) was set to %s minutes"),
    default="5"
)

welcome_message_title = ServerSetting(
    name="Welcome message title",
    description="The title of the embed in the welcome message. Not used if the message type is text. %s - server, %U - display name, %u - name of member, %m - mention of member",
    setting_type=SettingType.NORMAL,
    normal_view=setting_simple_string("Title of welcome messages is set to `%s`"),
    normal_response=setting_simple_string("Title of welcome messages was set to `%s`"),
    default="Welcome %m!"
)

welcome_message_message = ServerSetting(
    name="Welcome message",
    description="The text of the message or the content of the embed. %s - server, %U - display name, %u - name of member, %m - mention of member",
    setting_type=SettingType.NORMAL,
    normal_view=setting_simple_string("Message of welcome messages is set to `%s`"),
    normal_response=setting_simple_string("Message of welcome messages was set to `%s`"),
    default="Welcome %m to %s. Hope you enjoy your stay."
)

def validate_correct_type(c: Connection, m: Member, v: str) -> tuple[bool, str]:
    if v not in ["embed", "text"]:
        return False, "Invalid message type, must be one of `embed`, `text`"
    return True, ""

welcome_message_type = ServerSetting(
    name="Welcome message type",
    description="The type of the welcome message. Can be one of `text` or `embed`.",
    setting_type=SettingType.NORMAL,
    normal_processor=validate_correct_type,
    normal_view=setting_simple_string("Message of welcome messages is set to `%s`"),
    normal_response=setting_simple_string("Message of welcome messages was set to `%s`"),
    default="embed"
)

# Goodbye
goodbye_channel = ServerSetting(
    name="Goodbye channel",
    description="Set a channel to send goodbye messages into.",
    setting_type=SettingType.NORMAL,
    normal_processor=setting_to_text_channel,
    normal_view=setting_simple_string("Channel for saying goodbye to members is set to <#%s>"),
    normal_response=setting_simple_string("Channel for saying goodbye to members was set to <#%s>"),
    default="0"
)

goodbye_message_title = ServerSetting(
    name="Goodbye message title",
    description="The title of the embed in the goodbye message. Not used if the message type is text. %s - server, %U - display name, %u - name of member, %m - mention of member",
    setting_type=SettingType.NORMAL,
    normal_view=setting_simple_string("Title of goodbye messages is set to `%s`"),
    normal_response=setting_simple_string("Title of goodbye messages was set to `%s`"),
    default="Goodbye %u"
)

goodbye_message_message = ServerSetting(
    name="Goodbye message",
    description="The text of the message or the content of the embed. %s - server, %U - display name, %u - name of member, %m - mention of member",
    setting_type=SettingType.NORMAL,
    normal_view=setting_simple_string("Message of goodbye messages is set to `%s`"),
    normal_response=setting_simple_string("Message of goodbye messages was set to `%s`"),
    default="%s will miss you."
)

goodbye_message_type = ServerSetting(
    name="Goodbye message type",
    description="The type of the goodbye message. Can be one of `text` or `embed`.",
    setting_type=SettingType.NORMAL,
    normal_processor=validate_correct_type,
    normal_view=setting_simple_string("Message of goodbye messages is set to `%s`"),
    normal_response=setting_simple_string("Message of goodbye messages was set to `%s`"),
    default="embed"
)

grace_period_first = {}
grace_period_second = {}


def add_member_to_grace_period(c: Connection, member: Member):
    dur = int(welcome_grace_period_first.get(c, member))

    grace_period_first[uuid.uuid4()]= {
        'member': member,
        'after': datetime.datetime.now() + datetime.timedelta(seconds=dur)
    }


async def send_welcome_message(c: Connection, member: Member):
    chan = welcome_channel.get(c, member)
    if chan == "":
        return

    dur = int(welcome_grace_period_second.get(c, member))
    msg_type = welcome_message_type.get(c, member)
    title = welcome_message_title.get(c, member)
    msg = welcome_message_message.get(c, member)

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
                text="Nekona welcomes you too!" # TODO: turn the "Nekona" to a link
            )
        ))
        grace_period_second[uuid.uuid4()] ={
            'message': message,
            'member': member,
            'after': datetime.datetime.now() + datetime.timedelta(minutes=dur)
        }
    elif msg_type == "text":
        message = await chan.send(msg + "\nNekona welcomes you too!") # TODO: turn the "Nekona" to a link
        grace_period_second[uuid.uuid4()] ={
            'message': message,
            'member': member,
            'after': datetime.datetime.now() + datetime.timedelta(minutes=dur)
        }
    else:
        nekona_logger.warning("Invalid message type %s when welcoming member!", msg_type)

async def send_goodbye_message(c: Connection, member: Member):
    # Check first grace list
    for k, v in grace_period_first.items():
        if v['member'].id == member.id:
            nekona_logger.debug("Not sending goodbye message for %s, member is in join grace period", member.display_name)
            del grace_period_first[k]
            return

    # Check second grace list
    for k, v in grace_period_second.items():
        if v['member'].id == member.id:
            nekona_logger.debug("Deleting welcome message for %s", member.display_name)
            await v['message'].delete()
            nekona_logger.debug("Not sending goodbye message for %s, member is in second grace period", member.display_name)

            del grace_period_second[k]
            return

    chan = goodbye_channel.get(c, member)
    if chan == "":
        return

    msg_type = goodbye_message_type.get(c, member)
    title = goodbye_message_title.get(c, member)
    msg = goodbye_message_message.get(c, member)

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
        nekona_logger.warning("Invalid message type %s when saying goodbye to member!", msg_type)


async def handle_first_grace_period():
    discard_these = []
    global grace_period_first

    for k, v in grace_period_first.items():
        if v['after'] < datetime.datetime.now():
            nekona_logger.debug("Sending welcome message for %s", v['member'].display_name)
            discard_these.append(k)
            with engine.begin() as c:
                try:
                    await send_welcome_message(c, v['member'])
                except Exception:
                    nekona_logger.exception("Failed to send welcome message")

    for i in discard_these:
        del grace_period_first[i]


def handle_second_grace_period():
    discard_these = []
    global grace_period_second

    for k, v in grace_period_second.items():
        if v['after'] < datetime.datetime.now():
            nekona_logger.debug("Discarding second grace period for %s", v['member'].display_name)
            discard_these.append(k)

    for i in discard_these:
        del grace_period_second[i]


async def handle_timed_events():
    await handle_first_grace_period()
    handle_second_grace_period()
