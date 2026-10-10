import asyncio
import re

from discord import Message
from sqlalchemy import Connection, select, update

from database import counting_channels
from utils.server_settings import KV

same_member_counting_mode = KV(
    name="Counting same member mode",
    default="true",
)

any_count_mode = KV(
    name="Counting any count mode",
    default="false",
)

any_count_mode_count_frequency = KV(
    name="Counting any count mode: Count frequency of words",
    default="false",
)

any_count_mode_count_words = KV(
    name="Counting any count mode: Count total word count",
    default="false",
)

any_count_mode_minimum_frequency = KV(
    name="Counting any count mode: Minimum frequency",
    default="1",
)


def attempt_to_parse_number(c: Connection, m: Message) -> list[int]:
    if any_count_mode.get(c, m.guild.id) == "false":
        if not m.content.strip().isnumeric():
            return []

        return [int(m.content.strip())]

    numbers_in_message = []

    # Simple number parsing first
    for i in re.finditer(r"([0-9]+)", m.content.strip()):
        numbers_in_message.append(int(i.groups()[0]))

    # Count of words
    if any_count_mode_count_words.get(c, m.guild.id) == "true":
        numbers_in_message.append(len(m.content.strip().split(" ")))

    if any_count_mode_count_frequency.get(c, m.guild.id) == "true":
        # Count of words that repeat
        words = {}
        for i in m.content.strip().split(" "):
            if i not in words:
                words[i] = 0
            words[i] += 1

        try:
            a = int(any_count_mode_minimum_frequency.get(c, m.guild.id))
        except (TypeError, ValueError):
            a = 1
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

    # A row exists only for configured counting channels; a zeroed counter means
    # the count has not started yet. Configuration is the row itself.
    if a is None:
        return

    numbers = attempt_to_parse_number(c, msg)

    if a[0] == 0:
        if 1 in numbers:
            c.execute(
                update(counting_channels)
                .where(
                    (counting_channels.c.gid == str(msg.guild.id))
                    & (counting_channels.c.cid == str(msg.channel.id))
                )
                .values(current_count=2, last_counter=str(msg.author.id))
            )
            await msg.add_reaction("✅")
        else:
            await msg.add_reaction("❌")
        return

    same_member = True
    if same_member_counting_mode.get(c, msg.guild.id) == "true":
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
            update(counting_channels)
            .where(
                (counting_channels.c.gid == str(msg.guild.id))
                & (counting_channels.c.cid == str(msg.channel.id))
            )
            .values(current_count=0, last_counter="0")
        )
