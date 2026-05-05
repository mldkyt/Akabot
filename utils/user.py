import datetime

from sqlalchemy import insert, select

from database import engine, user


def bump_first_seen(user_id: str):
    with engine.begin() as c:
        if c.execute(
                select(user)
                        .where(user.c.id == str(user_id))
        ).fetchone() is None:
            c.execute(
                insert(user).values(id=str(user_id), firstseen=datetime.datetime.now(datetime.UTC))
            )


def get_first_seen(user_id: str | int) -> datetime.datetime:
    bump_first_seen(str(user_id))

    with engine.begin() as conn:
        # Safe variant usable on all
        first_seen = conn.execute(
            select(user.c.firstseen).where(user.c.id == str(user_id))
        ).fetchone()

    return first_seen[0]
