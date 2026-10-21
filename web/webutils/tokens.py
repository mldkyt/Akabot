import datetime

from flask import redirect, render_template, request, session
from sqlalchemy import select

from database import engine, web_tokens


def _is_expired(expires: datetime.datetime | None) -> bool:
    if expires is None:
        return True

    now = datetime.datetime.now(datetime.timezone.utc)

    if expires.tzinfo is None:
        # SQLite drops the offset when storing DateTime(timezone=True), so the
        # value read back is the naive UTC wall clock. PostgreSQL returns an
        # aware datetime and is compared as is.
        expires = expires.replace(tzinfo=datetime.timezone.utc)

    return expires <= now


def authorize(route: str):
    if "token" in request.args:
        session["token"] = request.args["token"]
        return redirect(route, 303)

    if "token" not in session:
        return render_template("unauthorized.html"), 401

    token_data = get_token_data(session["token"])
    if token_data is None:
        del session["token"]
        if "user" in session:
            del session["user"]

        return render_template("unauthorized.html"), 401

    session["user"] = {
        "name": token_data["user_name"],
        "avatar": token_data["user_avatar"],
        "guild": token_data["guild_name"],
        "guild_id": token_data["guild"],
    }

    return None


def get_token_data(token: str) -> dict | None:
    with engine.begin() as c:
        data = c.execute(
            select(
                web_tokens.c.gid,
                web_tokens.c.gname,
                web_tokens.c.uid,
                web_tokens.c.uname,
                web_tokens.c.uavatar,
                web_tokens.c.expires,
            ).where(web_tokens.c.token == token)
        ).fetchone()

    if data is None:
        return None

    if _is_expired(data[5]):
        return None

    return {
        "guild": data[0],
        "guild_name": data[1],
        "user": data[2],
        "user_name": data[3],
        "user_avatar": data[4],
    }
