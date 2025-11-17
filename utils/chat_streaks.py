from datetime import datetime, timedelta, date

from discord import Member
from sqlalchemy import Connection, select, insert, update, desc, func

from database import chat_streaks
from utils.server_settings import ServerSetting, SettingType, setting_is_boolean, setting_to_boolean, setting_is_number, \
    setting_simple_string_boolean, setting_simple_string
from utils.user_settings import UserSetting


def server_message_delay_validator(c: Connection, m: Member, v: str) -> tuple[bool, str]:
    ok, err = setting_is_number(c, m, v)
    if not ok:
        return ok, err

    v = int(v)
    if v < 3 or v > 10:
        return False, "Invalid number range"

    return True, ""

server_disable_response = ServerSetting(
    "Chat streaks disable response",
    setting_type=SettingType.NORMAL,
    normal_validator=setting_is_boolean,
    normal_transformer=setting_to_boolean,
    normal_response=setting_simple_string_boolean("The bot %s respond to messages with chat streak updates in this server", "WILL", "WON'T"),
    default="false"
)

user_disable_response = UserSetting(
    "Chat streaks disable response",
    setting_type=SettingType.NORMAL,
    normal_validator=setting_is_boolean,
    normal_transformer=setting_to_boolean,
    normal_response=setting_simple_string_boolean("The bot WON'T respond to messages with chat streak updates to you", "WON'T", "WILL"),
    default="false"
)

server_message_delay = ServerSetting(
    "Chat streaks message duration",
    setting_type=SettingType.NORMAL,
    normal_validator=server_message_delay_validator,
    normal_response=setting_simple_string("When the bot responds to a message, the bot message will be deleted after %s seconds"),
    default="5"
)

def update_for_user(c: Connection, u: Member):
    """Update chat streaks for a member"""

    now = date.today()
    yesterday = now - timedelta(days=1)

    # Check if we have an existant chat streak
    a = c.execute(
        select(chat_streaks.c.start_date, chat_streaks.c.last_message_date)
        .where((chat_streaks.c.uid == str(u.id)) & (chat_streaks.c.gid == str(u.guild.id)))
    ).fetchone()

    if a is None:
        c.execute(
            insert(chat_streaks)
            .values(gid=str(u.guild.id), uid=str(u.id),
                    start_date=yesterday,
                    last_message_date=now)
        )
    else:
        # Check days split
        last_message_date = a[1]
        diff = now - last_message_date

        if diff.days > 1:
            # Failed!
            c.execute(
                update(chat_streaks)
                .where((chat_streaks.c.uid == str(u.id)) & (chat_streaks.c.gid == str(u.guild.id)))
                .values(start_date=yesterday, last_message_date=now)
            )
        elif diff.days == 1:
            # Update
            c.execute(
                update(chat_streaks)
                .where((chat_streaks.c.uid == str(u.id)) & (chat_streaks.c.gid == str(u.guild.id)))
                .values(last_message_date=now)
            )

def get_streak(c: Connection, u: Member):
    """Get streak"""

    now = date.today()

    a = c.execute(
        select(chat_streaks.c.start_date, chat_streaks.c.last_message_date)
        .where((chat_streaks.c.uid == str(u.id)) & (chat_streaks.c.gid == str(u.guild.id)))
    ).fetchone()

    if a is None:
        return 0

    start_date = a[0]
    last_message_date = a[1]

    if (now - last_message_date).days > 1:
        return 0

    return (last_message_date - start_date).days

def get_leaderboard(c: Connection, u: Member):
    """Leaderboard"""

    a = c.execute(
        select(chat_streaks.c.uid, chat_streaks.c.start_date, chat_streaks.c.last_message_date)
        .where(chat_streaks.c.gid == str(u.guild.id))
        .order_by(
            desc(
                chat_streaks.c.last_message_date - chat_streaks.c.start_date
            )
        )
    ).fetchall()

    return a
