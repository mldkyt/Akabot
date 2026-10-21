from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import select, delete, insert, update

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
from web.webutils.quick_response import quick_response
from web.webutils.tokens import authorize, get_token_data

message_counting_bp = Blueprint(
    "message_counting", __name__, template_folder="templates"
)


def _parse_multiplier(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@message_counting_bp.route("/settings/message_counting", methods=["GET", "POST"])
def message_counting_index():
    authorization = authorize("/settings/message_counting")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        if request.method == "POST":
            section = request.form.get("_section", "general")
            if section == "general":
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

                return redirect("/settings/message_counting?tab=general", 303)

            action = request.form.get("action", "create")
            reward_id = request.form.get("id", "")
            reward_type = request.form.get("type", "")
            message_count = request.form.get("messages", "")

            if action == "delete" and reward_id.isnumeric():
                c.execute(
                    delete(message_counting_rewards).where(
                        (message_counting_rewards.c.id == int(reward_id))
                        & (message_counting_rewards.c.gid == auth["guild"])
                    )
                )
                flash("Deleted message counting reward")
            elif action == "update" and reward_id.isnumeric():
                if not message_count.isnumeric():
                    flash("Message count is not a number")
                elif reward_type == "multiplier":
                    multiplier = _parse_multiplier(request.form.get("multiplier"))
                    if multiplier is None:
                        flash("Multiplier is not a number")
                    else:
                        c.execute(
                            update(message_counting_rewards)
                            .where(
                                (message_counting_rewards.c.id == int(reward_id))
                                & (message_counting_rewards.c.gid == auth["guild"])
                            )
                            .values(
                                messages=int(message_count),
                                multiplier=multiplier,
                            )
                        )
                        flash("Saved message counting reward")
                elif reward_type == "role":
                    role_id = request.form.get("role", "")
                    role = c.execute(
                        select(synced_roles.c.rid).where(
                            (synced_roles.c.rid == role_id)
                            & (synced_roles.c.gid == auth["guild"])
                        )
                    ).fetchone()
                    if role is not None:
                        c.execute(
                            update(message_counting_rewards)
                            .where(
                                (message_counting_rewards.c.id == int(reward_id))
                                & (message_counting_rewards.c.gid == auth["guild"])
                            )
                            .values(messages=int(message_count), rid=role[0])
                        )
                        flash("Saved message counting reward")
                    else:
                        flash("Unknown role")
            elif action == "create":
                if not message_count.isnumeric():
                    flash("Message count is not a number")
                elif reward_type == "multiplier":
                    multiplier = _parse_multiplier(request.form.get("multiplier"))
                    if multiplier is None:
                        flash("Multiplier is not a number")
                    else:
                        c.execute(
                            insert(message_counting_rewards).values(
                                type="multiplier",
                                gid=auth["guild"],
                                messages=int(message_count),
                                multiplier=multiplier,
                            )
                        )
                        flash("Added multiplier reward")
                elif reward_type == "role" and "role" in request.form:
                    role_id = request.form["role"]
                    role = c.execute(
                        select(synced_roles.c.rid).where(
                            (synced_roles.c.rid == role_id)
                            & (synced_roles.c.gid == auth["guild"])
                        )
                    ).fetchone()
                    if role is None:
                        flash("Unknown role")
                    else:
                        c.execute(
                            insert(message_counting_rewards).values(
                                type="role",
                                gid=auth["guild"],
                                rid=role[0],
                                messages=int(message_count),
                            )
                        )
                        flash("Added role reward")

            return redirect("/settings/message_counting?tab=rewards", 303)

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
                    select(synced_roles.c.rname).where(
                        (synced_roles.c.rid == reward[3])
                        & (synced_roles.c.gid == auth["guild"])
                    )
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

    active_tab = request.args.get("tab", "general")
    if active_tab not in {"general", "rewards"}:
        active_tab = "general"

    return render_template(
        "message_counting.html",
        enable_leaderboard=enable_leaderboard,
        enable_indexer=enable_indexer,
        count_deletes=count_deletes,
        rewards=rewards,
        roles=roles,
        active_tab=active_tab,
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
