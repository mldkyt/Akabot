from flask import Blueprint, render_template, request, session
from sqlalchemy import select, delete, insert

from database import (
    engine,
    message_counting,
    message_counting_members,
    message_counting_rewards, synced_roles,
)
from utils.message_counting import (
    setting_count_deletes,
    setting_enable_indexer,
    setting_enable_leaderboard,
)
from utils.premium import get_limit
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

            # Delete reward
            if "remove" in request.form:
                remove_id = request.form["remove"]
                if not remove_id.isnumeric():
                    return quick_response("Invalid remove ID", 400)

                c.execute(
                    delete(message_counting_rewards)
                    .where(
                        (message_counting_rewards.c.id == int(remove_id))
                        & (message_counting_rewards.c.gid == auth["guild"])
                    )
                )

            # Role Reward
            elif "type" in request.form and "messages" in request.form:
                message_count = request.form["messages"]
                if not message_count.isnumeric():
                    return quick_response("Message count is not a number", 400)

                if request.form["type"] == "multiplier" and \
                    "multiplier" in request.form:
                    limit = get_limit(c, auth["guild"], 3)
                    reward_count = len(c.execute(
                        select(message_counting_rewards.c.id).where(message_counting_rewards.c.gid == auth["guild"])
                    ).fetchall())
                    if limit is not None and reward_count >= limit:
                        return quick_response("Free plan is limited to 3 rewards", 400)

                    multiplier = request.form["multiplier"]

                    c.execute(
                        insert(message_counting_rewards)
                        .values(type="multiplier", gid=auth["guild"], messages=int(message_count), multiplier=float(multiplier))
                    )

                if request.form["type"] == "role" and \
                    "role" in request.form:
                    limit = get_limit(c, auth["guild"], 3)
                    reward_count = len(c.execute(
                        select(message_counting_rewards.c.id).where(message_counting_rewards.c.gid == auth["guild"])
                    ).fetchall())
                    if limit is not None and reward_count >= limit:
                        return quick_response("Free plan is limited to 3 rewards", 400)

                    role_id = request.form["role"]
                    role = c.execute(
                        select(synced_roles.c.rid)
                        .where(synced_roles.c.rid == role_id)
                    ).fetchone()

                    if role is None:
                        return quick_response("Unknown role", 400)

                    c.execute(
                        insert(message_counting_rewards)
                        .values(type="role", gid=auth["guild"], rid=role[0], messages=int(message_count))
                    )

            else:
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

        rewards = []

        for reward in c.execute(
                select(
                    message_counting_rewards.c.id,
                    message_counting_rewards.c.type,
                    message_counting_rewards.c.messages,
                    message_counting_rewards.c.rid,
                    message_counting_rewards.c.multiplier
                ).where(
                    message_counting_rewards.c.gid == auth["guild"]
                )
        ).fetchall():
            if reward[1] == "multiplier":
                rewards.append(
                    {
                        "id": reward[0],
                        "type": reward[1],
                        "messages": reward[2],
                        "multiplier": reward[4],
                    }
                )
            elif reward[1] == "role":
                role_name = c.execute(
                    select(synced_roles.c.rname)
                    .where(synced_roles.c.rid == reward[3])
                ).fetchone()

                rewards.append(
                    {
                        "id": reward[0],
                        "type": reward[1],
                        "messages": reward[2],
                        "role_id": reward[3],
                        "role_name": role_name[0] if role_name else "Unknown role",
                    }
                )

        roles = [{
            "name": i[0],
            "id": i[1]
        } for i in c.execute(
            select(synced_roles.c.rname, synced_roles.c.rid)
            .where(synced_roles.c.gid == auth["guild"])
        )]

    with engine.begin() as c:
        premium = get_premium_context(c, auth["guild"])

    return render_template(
        "message_counting.html",
        enable_leaderboard=enable_leaderboard,
        enable_indexer=enable_indexer,
        count_deletes=count_deletes,
        rewards=rewards,
        roles=roles,
        premium=premium,
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
        members=leaderboard_users
    )
