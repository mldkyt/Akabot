import datetime

from sqlalchemy import insert, select, text

from database import engine, mail, mail_read
from utils.user import get_first_seen, bump_first_seen


def add_mail(author: str, text: str):
    with engine.begin() as c:
        c.execute(
            insert(mail)
            .values(
                text=text,
                author=author,
                created_at=datetime.datetime.now(datetime.UTC),
                updated_at=datetime.datetime.now(datetime.UTC)
            )
        )


def get_unread_mail(user_id: str) -> list[tuple[int, str, str, datetime.datetime]]:
    first_seen = get_first_seen(user_id)

    with engine.begin() as c:
        mai = c.execute(
            text(
                "SELECT id, text, author, created_at FROM mail WHERE id NOT IN (SELECT mail_id FROM mail_read WHERE user_id = :user_id) AND mail.created_at > :first_seen ORDER BY created_at DESC"),
            {"user_id": user_id, "first_seen": first_seen}
        ).fetchall()

    return mai


def get_unread_mail_count(user_id: str):
    bump_first_seen(user_id)

    with engine.begin() as c:
        unread = c.execute(
            text("SELECT COUNT(id) FROM mail "
                 "WHERE mail.created_at < (SELECT firstseen FROM user WHERE id = :user_id) OR EXISTS(SELECT 1 FROM mail_read WHERE mail_read.mail_id = mail.id AND mail_read.user_id = :user_id)"),
            {"user_id": user_id}
        ).fetchone()

    return unread[0]


def append_mail_footer(user_id: int):
    a = get_unread_mail_count(str(user_id))
    if a > 0:
        return f"You have {a} unread mails."

    return ""


def get_all_mail(user_id: str) -> list[tuple[int, str, str, bool]]:
    bump_first_seen(user_id)

    with engine.begin() as c:
        mai = c.execute(
            text(
                "SELECT mail.id, mail.text, mail.author, "
                "(mail.created_at < (SELECT firstseen FROM user WHERE id = :user_id) OR EXISTS(SELECT 1 FROM mail_read WHERE mail_read.mail_id = mail.id AND mail_read.user_id = :user_id)) "
                "FROM mail ORDER BY created_at DESC"),
            {"user_id": user_id}
        ).fetchall()

    return mai


def mark_as_read(user_id: str, mail_id: int):
    with engine.begin() as c:
        c.execute(
            insert(mail_read)
            .values(user_id=user_id, mail_id=mail_id, read_at=datetime.datetime.now(datetime.UTC))
        )


def get_mail_by_id(id: int):
    with engine.begin() as c:
        return c.execute(
            select(mail.c.id, mail.c.text, mail.c.author, mail.c.created_at)
            .where(mail.c.id == id)
        ).fetchone()
