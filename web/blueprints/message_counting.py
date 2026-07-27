from flask import Blueprint, render_template, request, session
from sqlalchemy import select

from database import engine, message_counting, message_counting_members
from utils.message_counting import (
    setting_count_deletes,
    setting_enable_indexer,
    setting_enable_leaderboard,
)
from web.webutils.quick_response import quick_response
from web.webutils.tokens import authorize, get_token_data

message_counting_bp = Blueprint(
    "message_counting", __name__, template_folder="templates"
)


@message_counting_bp.route("/settings/message_counting", methods=["GET", "POST"])
def message_counting_index():
    authorization = authorize("/settings/message_counting")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        if request.method == "POST":
            if request.form.get("enable_leaderboard"):
                setting_enable_leaderboard.set(c, auth["guild"], "true")
            else:
                setting_enable_leaderboard.set(c, auth["guild"], "false")

            if request.form.get("enable_indexer"):
                setting_enable_indexer.set(c, auth["guild"], "true")
            else:
                setting_enable_indexer.set(c, auth["guild"], "false")

            if request.form.get("count_deletes"):
                setting_count_deletes.set(c, auth["guild"], "true")
            else:
                setting_count_deletes.set(c, auth["guild"], "false")

        enable_leaderboard = setting_enable_leaderboard.get(c, auth["guild"]) == "true"
        enable_indexer = setting_enable_indexer.get(c, auth["guild"]) == "true"
        count_deletes = setting_count_deletes.get(c, auth["guild"]) == "true"

    return render_template(
        "message_counting.html",
        enable_leaderboard=enable_leaderboard,
        enable_indexer=enable_indexer,
        count_deletes=count_deletes,
    )


@message_counting_bp.route("/leaderboard/<id>")
def message_counting_leaderboard(id: str):
    with engine.begin() as c:
        leaderboard = c.execute(
            select(message_counting.c.name, message_counting.c.messages).where(
                message_counting.c.gid == id
            )
        ).fetchone()

        if not leaderboard:
            return quick_response("Discord Server not found", 404)

        leaderboard_users = [
            {"name": i[0], "messages": i[1]}
            for i in c.execute(
                select(
                    message_counting_members.c.name, message_counting_members.c.messages
                )
                .where(message_counting_members.c.gid == id)
                .order_by(message_counting_members.c.messages.desc())
            ).fetchall()
        ]

        leaderboard_enabled = setting_enable_leaderboard.get(c, id) == "true"

        if not leaderboard_enabled:
            return quick_response(
                "This Discord server has the leaderboard disabled", 400
            )

    return render_template(
        "web_leaderboard.html",
        guild_name=leaderboard[0],
        messages=leaderboard[1],
        members=leaderboard_users,
    )
