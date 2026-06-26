import datetime

from sqlalchemy import select

from database import engine, mail


def get_all_mail() -> list[tuple[int, str, str, datetime.datetime, datetime.datetime]]:
    with engine.begin() as c:
        mai = c.execute(
            select(mail.c.id, mail.c.author, mail.c.text, mail.c.created_at, mail.c.updated_at)
            .order_by(mail.c.created_at.desc())
        ).fetchall()

    return mai
