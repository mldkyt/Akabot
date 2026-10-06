import datetime
import random
from zoneinfo import ZoneInfo

from discord import Message, Member, User, ButtonStyle, Button, Interaction
from discord.ui import View, button
from sqlalchemy import insert, select, delete, update, text

from database import engine, giveaways, giveaway_joins
from utils.timezones import get_now, get_timezone


class GiveawayView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Join", style=ButtonStyle.primary, custom_id="giveaway:join")
    async def join(self, button: Button, interaction: Interaction):
        assert interaction.message is not None
        assert interaction.user is not None

        if has_joined_giveaway(interaction.message, interaction.user):
            ok = leave_giveaway(interaction.message, interaction.user)
            if not ok:
                await interaction.respond("Failed to leave the giveaway, maybe it ended?", ephemeral=True)
            else:
                await interaction.respond("You have left the giveaway", ephemeral=True)
        else:
            ok = join_giveaway(interaction.message, interaction.user)
            if not ok:
                await interaction.respond("Failed to join giveaway, maybe it ended?", ephemeral=True)
            else:
                await interaction.respond("You have joined the giveaway", ephemeral=True)


class GiveawayEndedView(View):
    def __init__(self, gid: int):
        super().__init__(disable_on_timeout=True)
        self.gid = gid

    @button(label="Reroll", style=ButtonStyle.secondary)
    async def reroll(self, button: Button, interaction: Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.respond("You must have manage guild to reroll", ephemeral=True)
            return

        winner = reroll_winner(self.gid)

        if winner is None:
            await interaction.respond("No one left to reroll", ephemeral=True)
            return

        await interaction.respond(f"Reroll winner: <@{winner}>")


def create_giveaway(initial_message: Message, winners: int, end_date: datetime.datetime) -> int:
    assert initial_message.guild is not None

    with engine.begin() as c:
        res = c.execute(
            insert(giveaways)
            .values(gid=str(initial_message.guild.id), cid=str(initial_message.channel.id), mid=str(initial_message.id),
                    winners=winners, end=end_date, expiry=end_date + datetime.timedelta(hours=1))
            .returning(giveaways.c.id)
        ).fetchone()

    return res[0]


def get_ending_giveaways() -> list[tuple[int, str, str, str]]:
    with engine.begin() as c:
        res = c.execute(
            select(giveaways.c.id, giveaways.c.gid, giveaways.c.cid, giveaways.c.mid, giveaways.c.end)
            .where(giveaways.c.end.is_not(None))
        ).fetchall()

    ending = []
    for i in res:
        end = i[4]
        # On Postgres, DateTime(timezone=True) comes back timezone-aware;
        # convert to the guild's naive local wall time before comparing.
        if end.tzinfo is not None:
            end = end.astimezone(ZoneInfo(get_timezone(int(i[1])))).replace(tzinfo=None)
        if end < get_now(int(i[1])):
            ending.append((i[0], i[1], i[2], i[3]))

    return ending


def mark_giveaway_ended(gid: int):
    with engine.begin() as c:
        c.execute(
            update(giveaways)
            .where(giveaways.c.id == gid)
            .values(end=None)
        )


def clear_expired_giveaways():
    with engine.begin() as c:
        res = c.execute(
            select(giveaways.c.id, giveaways.c.gid, giveaways.c.expiry)
        ).fetchall()

        for i in res:
            expiry = i[2]
            if expiry.tzinfo is not None:
                expiry = expiry.astimezone(ZoneInfo(get_timezone(int(i[1]), c))).replace(tzinfo=None)
            if expiry >= get_now(int(i[1]), c):
                continue

            c.execute(
                delete(giveaway_joins)
                .where(giveaway_joins.c.gid == i[0])
            )
            c.execute(
                delete(giveaways)
                .where(giveaways.c.id == i[0])
            )


def join_giveaway(giveaway_message: Message, user: Member | User) -> bool:
    with engine.begin() as c:
        # First check
        giveaway = c.execute(
            select(giveaways.c.id, giveaways.c.end)
            .where((giveaways.c.mid == str(giveaway_message.id)))
        ).fetchone()

        if giveaway is None:
            return False
        if giveaway[1] is None:
            return False

        res = c.execute(
            select(giveaway_joins)
            .where((giveaway_joins.c.gid == giveaway[0]) & (giveaway_joins.c.uid == str(user.id)))
        ).fetchone()

        if res is not None:
            return False

        c.execute(
            insert(giveaway_joins)
            .values(gid=giveaway[0], uid=str(user.id))
        )

    return True


def has_joined_giveaway(giveaway_message: Message, user: Member | User):
    with engine.begin() as c:
        # First check
        giveaway = c.execute(
            select(giveaways.c.id)
            .where((giveaways.c.mid == str(giveaway_message.id)))
        ).fetchone()

        if giveaway is None:
            return True

        res = c.execute(
            select(giveaway_joins)
            .where((giveaway_joins.c.gid == giveaway[0]) & (giveaway_joins.c.uid == str(user.id)))
        ).fetchone()

        if res is not None:
            return True

    return False


def leave_giveaway(giveaway_message: Message, user: Member | User) -> bool:
    with engine.begin() as c:
        # First check
        giveaway = c.execute(
            select(giveaways.c.id, giveaways.c.end)
            .where((giveaways.c.mid == str(giveaway_message.id)))
        ).fetchone()

        if giveaway is None:
            return False
        if giveaway[1] is None:
            return False

        res = c.execute(
            delete(giveaway_joins)
            .where((giveaway_joins.c.gid == giveaway[0]) & (giveaway_joins.c.uid == str(user.id)))
        )

    return res.rowcount > 0


def roll_winners(message: Message) -> list[str]:
    """Roll as many winners as are specified in the giveaway."""
    with engine.begin() as c:
        res = c.execute(
            select(giveaways.c.id, giveaways.c.winners)
            .where(giveaways.c.mid == str(message.id))
        ).fetchone()

        if res is None:
            return []

        winners_db = c.execute(
            select(giveaway_joins.c.uid)
            .where(giveaway_joins.c.gid == res[0])
        ).fetchall()

        winners = random.sample(winners_db, k=min(len(winners_db), res[1]))

        for i in winners:
            c.execute(
                delete(giveaway_joins)
                .where((giveaway_joins.c.gid == res[0]) & (giveaway_joins.c.uid == i[0]))
            )

    return [i[0] for i in winners]


def reroll_winner(gid: int) -> str | None:
    """Roll one winner."""
    with engine.begin() as c:
        res = c.execute(
            select(giveaways.c.id, giveaways.c.winners)
            .where(giveaways.c.id == gid)
        ).fetchone()

        if res is None:
            return None

        winners_db = c.execute(
            select(giveaway_joins.c.uid)
            .where(giveaway_joins.c.gid == res[0])
        ).fetchall()

        if len(winners_db) == 0:
            return None

        winner = random.choice(winners_db)

        c.execute(
            delete(giveaway_joins)
            .where((giveaway_joins.c.gid == res[0]) & (giveaway_joins.c.uid == winner[0]))
        )

    return winner[0]


def get_giveaway_joins(msg_id: str):
    with engine.begin() as c:
        res = c.execute(
            select(giveaways.c.id)
            .where(giveaways.c.mid == msg_id)
        ).fetchone()

        if res is None:
            return None

        res = c.execute(
            text("SELECT COUNT(*) FROM giveaway_joins WHERE giveaway_joins.gid = :id"),
            {"id": res[0]}
        ).fetchone()

    return res[0]


def get_giveaway_info_by_mid(mid: str) -> tuple[int, str, str, str, bool] | None:
    with engine.begin() as c:
        res = c.execute(
            select(giveaways.c.id, giveaways.c.gid, giveaways.c.cid, giveaways.c.mid, giveaways.c.end)
            .where(giveaways.c.mid == mid)
        ).fetchone()

        if res is None:
            return None

        return res[0], res[1], res[2], res[3], res[4] is None
