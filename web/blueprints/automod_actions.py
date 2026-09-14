from flask import Blueprint, request, render_template, session, flash, redirect
from sqlalchemy import select, Connection

from database import engine, synced_automod_rules
from utils.automod_actions import automod_actions, time_str_to_time
from utils.premium import get_limit
from web.webutils.discord_sync import validate_automod_rule_id
from web.webutils.tokens import authorize, get_token_data

automod_actions_bp = Blueprint("automod_actions", __name__, template_folder='templates')


def parse_automod_action(c: Connection, index: int, args: tuple) -> dict:
    output = {
        "id": index,
        "rule": args[0],
        "action": args[1]
    }

    extra = c.execute(
        select(synced_automod_rules.c.aname)
        .where(synced_automod_rules.c.aid == args[0])
    ).fetchone()
    if extra is not None:
        output["name"] = extra[0]

    if len(args) == 4:
        if args[1] == "mute":
            output["time"] = args[2]
            output["reason"] = args[3]
    elif len(args) == 3:
        if args[1] in ["kick", "ban"]:
            output["reason"] = args[2]
        if args[1] in ["dm"]:
            output["message"] = args[2]

    return output


def parse_automod_actions(guild_id: int) -> list[dict]:
    automod_action_list = []
    with engine.begin() as c:
        automod_actions_rules = automod_actions.get(c, guild_id)
        for index in range(len(automod_actions_rules)):
            automod_action = automod_actions_rules[index]
            args = automod_action.split(";")
            output = parse_automod_action(c, index, args)

            automod_action_list.append(output)

    return automod_action_list


def handle_create_automod_action(is_edit: bool = False) -> bool:
    auth = get_token_data(session["token"])
    assert auth is not None

    if "type" not in request.form and "rule" not in request.form:
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

    setting_str = ""
    if request.form["type"] in ["kick", "ban"]:
        setting_str = f"{request.form['rule']};{request.form['type']}" + ((";" + reason) if reason is not None else "")
    elif request.form["type"] == "dm":
        setting_str = f"{request.form['rule']};{request.form['type']};{request.form['message']}"
    elif request.form["type"] == "mute":
        setting_str = f"{request.form['rule']};{request.form['type']};{request.form['time']}" + (
            (";" + reason) if reason is not None else "")

    with engine.begin() as c:
        limit = get_limit(c, int(auth["guild"]), 3)
        if limit is not None and len(automod_actions.get(c, int(auth["guild"]))) >= limit:
            flash("Free plan is limited to 3 automod actions")
            return False

        automod_actions.add_to_list(c, int(auth["guild"]), setting_str)

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
        handle_create_automod_action()

    auth = get_token_data(session["token"])
    assert auth is not None
    automod_actions = parse_automod_actions(auth['guild'])
    automod_rules = get_automod_rules(auth['guild'])

    return render_template("automod_actions.html", automod_actions=automod_actions, automod_rules=automod_rules)


@automod_actions_bp.route("/settings/automod_actions/delete/<index>")
def automod_actions_delete(index: str):
    authorization = authorize("/settings/automod_actions")
    if authorization is not None:
        return authorization

    if not index.isnumeric():
        return redirect("/settings/automod_actions", 302)

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        the_list = automod_actions.get(c, auth["guild"])
        if len(the_list) <= int(index):
            flash("Can't delete item outside of range")
            return redirect("/settings/automod_actions", 302)

        parsed = parse_automod_action(c, int(index), the_list[int(index)].split(";"))

    if "confirm" in request.args and request.args["confirm"] == "yes":
        with engine.begin() as c:
            automod_actions.remove_from_list(c, auth["guild"], the_list[int(index)])
            return redirect("/settings/automod_actions", 302)

    return render_template("automod_actions_delete.html", action=parsed)


@automod_actions_bp.route("/settings/automod_actions/edit/<index>", methods=["POST"])
def automod_actions_edit(index: str):
    authorization = authorize("/settings/automod_actions")
    if authorization is not None:
        return authorization

    if not index.isnumeric():
        return redirect("/settings/automod_actions", 302)

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        the_list = automod_actions.get(c, auth["guild"])
        if len(the_list) <= int(index):
            flash("Can't edit item outside of range")
            return redirect("/settings/automod_actions", 302)

        the_list = automod_actions.get(c, auth["guild"])
        automod_actions.remove_from_list(c, auth["guild"], the_list[int(index)])

    handle_create_automod_action(is_edit=True)
    return redirect("/settings/automod_actions", 302)
