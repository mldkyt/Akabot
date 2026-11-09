import datetime
from typing import Any, AsyncGenerator

from discord import Bot, ButtonStyle
from discord.ui import View, ViewItem, Button
from discord.ui.view import V
from sqlalchemy import insert, select, delete

from database import engine, reminders

async def schedule_reminder(uid: int, content: str, timedelta: datetime.timedelta):
    now = datetime.datetime.now(datetime.UTC)
    remind_at = now + timedelta

    with engine.begin() as c:
        c.execute(
            insert(reminders)
            .values(
                uid=str(uid),
                content=content,
                remind_at=remind_at,
            )
        )

async def reminders_going_off() -> AsyncGenerator[tuple[Any, Any], Any]:
    with engine.begin() as c:
        iterator = c.execute(
            select(reminders.c.uid, reminders.c.content)
            .where(reminders.c.remind_at < datetime.datetime.now(datetime.UTC))
        )

        fetch = iterator.fetchone()
        while fetch is not None:
            yield int(fetch.uid), fetch.content
            fetch = iterator.fetchone()


async def mark_reminders_as_read(*uids: int):
    with engine.begin() as c:
        c.execute(
            delete(reminders)
            .where(reminders.c.uid.in_(uids))
        )


class AddAkabotAsUserInstall(View):
    def __init__(
        self,
        bot: Bot
    ):
        super().__init__()

        self.add_item(
            Button(
                style=ButtonStyle.url,
                label="Add Akabot",
                url=f"https://discord.com/oauth2/authorize?client_id={bot.application_id}"
            )
        )
