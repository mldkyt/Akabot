from flask import make_response, redirect, request, session
from sqlalchemy import select

from database import engine, web_tokens


def authorize(route: str):
    if "token" in request.args:
        session["token"] = request.args["token"]
        return redirect(route, 303)

    if "token" not in session:
        response = make_response("Unauthorized")
        response.status_code = 401
        return response

    token_data = get_token_data(session["token"])
    if token_data is None:
        del session["token"]
        if "user" in session:
            del session["user"]

        response = make_response("Unauthorized")
        response.status_code = 401
        return response

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
            ).where(web_tokens.c.token == token)
        ).fetchone()

    if data is None:
        return None

    return {
        "guild": data[0],
        "guild_name": data[1],
        "user": data[2],
        "user_name": data[3],
        "user_avatar": data[4],
    }
