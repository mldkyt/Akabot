import asyncio
import re

from discord import Message
from sqlalchemy import Connection, delete, insert, select, update

from database import counting_channels
from utils.server_settings import (
    ServerSetting,
    SettingType,
    setting_to_number,
    setting_simple_list_string,
    setting_simple_string,
    setting_simple_string_boolean,
    setting_to_boolean,
    setting_to_text_channel,
)

setting_counting_channels = ServerSetting(
    name="Counting channels",
    description='The list of channels that should be considered "counting channels". Any channels in this list will be marked as counting channels.',
    setting_type=SettingType.LIST,
    list_add_processor=setting_to_text_channel,
    list_remove_processor=setting_to_text_channel,
    list_add_response=setting_simple_string(
        "Channel <#%s> was added to counting channels."
    ),
    list_remove_response=setting_simple_string(
        "Channel <#%s> was removed from counting channels."
    ),
    list_view=setting_simple_list_string(
        "Counting channels: %s", ", ", "Counting channels: None"
    ),
)

same_member_counting_mode = ServerSetting(
    name="Counting same member mode",
    description='Determines if a member can count twice consecutively or not. If set to "no", it will let anyone count as many times as they wish.',
    setting_type=SettingType.NORMAL,
    normal_processor=setting_to_boolean,
    normal_response=setting_simple_string_boolean(
        "Same member counting mode is %s", "enabled", "disabled"
    ),
    normal_view=setting_simple_string_boolean(
        "Same member counting mode is currently %s", "enabled", "disabled"
    ),
    default="true",
)

any_count_mode = ServerSetting(
    name="Counting any count mode",
    description="Instead of explicitly checking for numbers, check for numbers in the entire message instead. Allows members to add anything to the message.",
    setting_type=SettingType.NORMAL,
    normal_processor=setting_to_boolean,
    normal_response=setting_simple_string_boolean(
        "Any count mode is now %s", "enabled", "disabled"
    ),
    normal_view=setting_simple_string_boolean(
        "Any count mode is currently %s", "enabled", "disabled"
    ),
    default="false",
)

any_count_mode_count_frequency = ServerSetting(
    name="Counting any count mode: Count frequency of words",
    description="If any count mode is enabled, a number is also how many times has one word appeared in the counting message.",
    setting_type=SettingType.NORMAL,
    normal_processor=setting_to_boolean,
    normal_response=setting_simple_string_boolean(
        "Any count mode %s count frequencies of words", "will", "won't"
    ),
    normal_view=setting_simple_string_boolean(
        "Any count mode %s frequencies of words", "counts", "doesn't count"
    ),
    default="false",
)

any_count_mode_count_words = ServerSetting(
    name="Counting any count mode: Count total word count",
    description="If any count mode is enabled, a number is also how many words are in the message.",
    setting_type=SettingType.NORMAL,
    normal_processor=setting_to_boolean,
    normal_response=setting_simple_string_boolean(
        "Any count mode %s count total words", "will", "won't"
    ),
    normal_view=setting_simple_string_boolean(
        "Any count mode %s total words", "counts", "doesn't count"
    ),
    default="false",
)

any_count_mode_minimum_frequency = ServerSetting(
    name="Counting any count mode: Minimum frequency",
    description="If any count mode: count frequency of words is enabled, this is the minimum amount of that word has to be in the message to be considered as a number.",
    setting_type=SettingType.NORMAL,
    normal_processor=setting_to_number,
    normal_response=setting_simple_string(
        "Any count mode's minimum frequency is `%s`, words less frequent than this are not counted"
    ),
    normal_view=setting_simple_string(
        "Any count's minimum frequency of words is currently `%s`, words less frequent are not counted"
    ),
    default="false",
)


def attempt_to_parse_number(c: Connection, m: Message) -> list[int]:
    if any_count_mode.get(c, m.author) == "false":
        if not m.content.strip().isnumeric():
            return []

        return [int(m.content.strip())]

    numbers_in_message = []

    # Simple number parsing first
    for i in re.finditer(r"([0-9]+)", m.content.strip()):
        numbers_in_message.append(int(i.groups()[0]))

    # Count of words
    if any_count_mode_count_words.get(c, m.author) == "true":
        numbers_in_message.append(len(m.content.strip().split(" ")))

    if any_count_mode_count_frequency.get(c, m.author) == "true":
        # Count of words that repeat
        words = {}
        for i in m.content.strip().split(" "):
            if i not in words:
                words[i] = 0
            words[i] += 1

        a = int(any_count_mode_minimum_frequency.get(c, m.author))
        less_frequent_words = []
        for k in words.keys():
            if words[k] < a:
                less_frequent_words.append(k)

        for i in less_frequent_words:
            del words[i]

        words = {
            k: v for k, v in sorted(words.items(), key=lambda x: x[1], reverse=True)
        }
        numbers_in_message.extend([i for i in words.values()])

    return numbers_in_message


async def handle_counting_channel(c: Connection, msg: Message):
    a = c.execute(
        select(
            counting_channels.c.current_count, counting_channels.c.last_counter
        ).where(
            (counting_channels.c.gid == str(msg.guild.id))
            & (counting_channels.c.cid == str(msg.channel.id))
        )
    ).fetchone()

    numbers = attempt_to_parse_number(c, msg)

    if a is None:
        if 1 in numbers:
            c.execute(
                insert(counting_channels).values(
                    gid=str(msg.guild.id),
                    cid=str(msg.channel.id),
                    current_count=2,
                    last_counter=str(msg.author.id),
                )
            )
            await msg.add_reaction("✅")
        else:
            await msg.add_reaction("❌")
    else:
        same_member = True
        if same_member_counting_mode.get(c, msg.author) == "true":
            same_member = a[1] != str(msg.author.id)

        if a[0] in numbers and same_member:
            c.execute(
                update(counting_channels)
                .where(
                    (counting_channels.c.gid == str(msg.guild.id))
                    & (counting_channels.c.cid == str(msg.channel.id))
                )
                .values(current_count=a[0] + 1, last_counter=str(msg.author.id))
            )
            await msg.add_reaction("✅")
        else:
            await asyncio.gather(
                msg.channel.send(
                    f"Awww, {msg.author.mention} ruined the count at {a[0]}!"
                ),
                msg.add_reaction("❌"),
            )

            c.execute(
                delete(counting_channels).where(
                    (counting_channels.c.gid == str(msg.guild.id))
                    & (counting_channels.c.cid == str(msg.channel.id))
                )
            )
