from flask import Blueprint, request, render_template, session, flash, redirect
from sqlalchemy import Connection, delete, insert, select, update

from database import automod_actions, engine, synced_automod_rules
from utils.automod_actions import setting_automod_sync_error
from utils.automod_actions import time_str_to_time
from web.webutils.discord_sync import validate_automod_rule_id
from web.webutils.tokens import authorize, get_token_data

automod_actions_bp = Blueprint("automod_actions", __name__, template_folder='templates')


def parse_automod_action(c: Connection, guild_id: int, index: int, row: tuple) -> dict:
    output = {
        "id": row[0],
        "index": index,
        "rule": row[1],
        "action": row[2]
    }

    extra = c.execute(
        select(synced_automod_rules.c.aname)
        .where(
            (synced_automod_rules.c.aid == row[1])
            & (synced_automod_rules.c.gid == str(guild_id))
        )
    ).fetchone()
    if extra is not None:
        output["name"] = extra[0]

    if row[2] == "mute":
        if row[3] is not None:
            output["time"] = row[3]
        if row[4] is not None:
            output["reason"] = row[4]
    elif row[2] in ["kick", "ban"]:
        if row[4] is not None:
            output["reason"] = row[4]
    elif row[2] in ["dm"]:
        if row[4] is not None:
            output["message"] = row[4]

    return output


def parse_automod_actions(guild_id: int) -> list[dict]:
    automod_action_list = []
    with engine.begin() as c:
        rows = c.execute(
            select(
                automod_actions.c.id,
                automod_actions.c.rule_id,
                automod_actions.c.action,
                automod_actions.c.duration,
                automod_actions.c.content,
            )
            .where(automod_actions.c.gid == str(guild_id))
            .order_by(automod_actions.c.id)
        ).fetchall()
        for index in range(len(rows)):
            output = parse_automod_action(c, guild_id, index, rows[index])

            automod_action_list.append(output)

    return automod_action_list


def handle_create_automod_action(is_edit: bool = False, action_id: int | None = None) -> bool:
    auth = get_token_data(session["token"])
    assert auth is not None

    if "type" not in request.form or "rule" not in request.form:
        flash("Missing form parameters")
        return False

    if not validate_automod_rule_id(request.form["rule"]):
        flash("Invalid automod action rule")
        return False

    if request.form["type"] not in ["dm", "kick", "ban", "mute"]:
        flash("Invalid automod action type")
        return False

    if request.form["type"] == "mute" and (
            "time" not in request.form or time_str_to_time(request.form["time"]) is None):
        flash("Invalid or missing time (mute type)")
        return False

    if request.form["type"] == "dm" and ("message" not in request.form or len(request.form["message"].strip()) < 4):
        flash("The message is missing or too short")
        return False

    reason = None
    if "reason" in request.form and len(request.form["reason"].strip()) > 4:
        reason = request.form["reason"]

    duration = None
    content = None
    if request.form["type"] == "mute":
        duration = request.form["time"]
        content = reason
    elif request.form["type"] in ["kick", "ban"]:
        content = reason
    elif request.form["type"] == "dm":
        content = request.form["message"]

    with engine.begin() as c:
        values = {
            "rule_id": request.form["rule"],
            "action": request.form["type"],
            "duration": duration,
            "content": content,
        }
        if is_edit and action_id is not None:
            c.execute(
                update(automod_actions)
                .where(
                    (automod_actions.c.id == action_id)
                    & (automod_actions.c.gid == str(auth["guild"]))
                )
                .values(**values)
            )
        else:
            c.execute(
                insert(automod_actions).values(
                    gid=str(auth["guild"]),
                    **values,
                )
            )

    if is_edit:
        flash("Edited successfully")
    else:
        flash("Created successfully")

    return True


def get_automod_rules(guild_id: int):
    with engine.begin() as c:
        return [{
            "id": i[1],
            "name": i[0]
        } for i in c.execute(
            select(synced_automod_rules.c.aname, synced_automod_rules.c.aid)
            .where(synced_automod_rules.c.gid == str(guild_id))
        ).fetchall()]


@automod_actions_bp.route("/settings/automod_actions", methods=["GET", "POST"])
def automod_actions_index():
    authorization = authorize("/settings/automod_actions")
    if authorization is not None:
        return authorization

    if request.method == "POST":
        action = request.form.get("action", "create")
        if action == "update":
            action_id = request.form.get("id", "")
            if action_id.isnumeric():
                handle_create_automod_action(is_edit=True, action_id=int(action_id))
            else:
                flash("Invalid action id")
        elif action == "delete":
            action_id = request.form.get("id", "")
            if action_id.isnumeric():
                auth = get_token_data(session["token"])
                assert auth is not None
                with engine.begin() as c:
                    c.execute(
                        delete(automod_actions).where(
                            (automod_actions.c.id == int(action_id))
                            & (automod_actions.c.gid == auth["guild"])
                        )
                    )
                flash("Deleted automod action")
            else:
                flash("Invalid action id")
        else:
            handle_create_automod_action()
        return redirect(
            f"/settings/automod_actions?tab={request.form.get('_tab', 'actions')}", 303
        )

    auth = get_token_data(session["token"])
    assert auth is not None
    active_tab = request.args.get("tab", "actions")
    if active_tab not in {"create", "actions"}:
        active_tab = "actions"
    automod_action_list = parse_automod_actions(auth['guild'])
    automod_rules = get_automod_rules(auth['guild'])

    with engine.begin() as c:
        automod_sync_error = setting_automod_sync_error.get(c, auth["guild"]) or ""

    return render_template(
        "automod_actions.html",
        automod_actions=automod_action_list,
        automod_rules=automod_rules,
        automod_sync_error=automod_sync_error,
        active_tab=active_tab,
    )
