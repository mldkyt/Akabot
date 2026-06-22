import re
from datetime import datetime

from flask import Blueprint, session, render_template, request, flash, redirect
from sqlalchemy import select

from database import engine, synced_roles
from utils.leveling import setting_xp_per_message, setting_level_up_message, setting_level_up_message_text, \
    setting_xp_per_level, setting_leveling_rewards, setting_leveling_multipliers
from web.webutils.discord_sync import validate_role_id
from web.webutils.tokens import authorize, get_token_data

leveling_bp = Blueprint("leveling", __name__, template_folder='templates')

def handle_settings(auth):
    if "reward_role" in request.form:
        return
    if "multiplier" in request.form:
        return

    with engine.begin() as c:
        if request.form.get("level_up_message"):
            setting_level_up_message.direct_set(c, auth["guild"], "true")
        else:
            setting_level_up_message.direct_set(c, auth["guild"], "false")

        level_up_message_text = request.form.get("level_up_message_text")

        if level_up_message_text:
            if 2 < len(level_up_message_text) < 250:
                setting_level_up_message_text.direct_set(c, auth["guild"], level_up_message_text)
            else:
                flash("Invalid length of level up message text")

        xp_per_message = request.form.get("xp_per_message")
        if xp_per_message:
            if xp_per_message.isnumeric() and 1 <= int(xp_per_message) <= 100:
                setting_xp_per_message.direct_set(c, auth["guild"], xp_per_message)
            else:
                flash("XP per message must be between 1 and 100")

        xp_per_level = request.form.get("xp_per_level")
        if xp_per_level:
            if xp_per_level.isnumeric() and 10 <= int(xp_per_level) <= 10000:
                setting_xp_per_level.direct_set(c, auth["guild"], xp_per_level)
            else:
                flash("XP per level must be between 10 and 10000")

def handle_rewards(auth, is_edit: bool = False):
    reward_role = request.form.get("reward_role")
    required_level = request.form.get("required_level")

    if not reward_role or not required_level:
        return

    if not validate_role_id(reward_role):
        flash("Role not found, try adding again if you just edited roles.")
        return

    if not required_level.isnumeric() or 1 > int(required_level) > 1000:
        flash("The level must be between 1 and 1000")
        return

    with engine.begin() as c:
        setting_leveling_rewards.add_to_list(c, auth["guild"], f"{reward_role};{required_level}")
        if is_edit:
            flash("Edited role reward successfully")
        else:
            flash("Added role reward successfully")

def handle_multipliers(auth):
    start = request.form.get("start")
    end = request.form.get("end")
    multiplier = request.form.get("multiplier")

    if not start or not end or not multiplier:
        return
    if not multiplier.isnumeric():
        return

    if not re.match(r"^(\d)+-(\d)+$", start):
        flash("Invalid format for start date for multiplier")
        return

    start_month, start_day = start.split("-")

    try:
        datetime(2024, int(start_month), int(start_day))
    except Exception:
        flash("Failed to parse start date")
        return

    if not re.match(r"^(\d)+-(\d)+$", end):
        flash("Invalid format for end date for multiplier")
        return

    end_month, end_day = end.split("-")

    try:
        datetime(2024, int(end_month), int(end_day))
    except Exception:
        flash("Failed to parse end date")
        return

    if 1 > int(multiplier) > 1000:
        flash("Multiplier must be between 1 and 1000")
        return

    with engine.begin() as c:
        setting_leveling_multipliers.add_to_list(c, auth["guild"], f"{start_month:02}-{start_day:02};{end_month:02}-{end_day:02};{multiplier}")


@leveling_bp.route('/settings/leveling', methods=["GET", "POST"])
def leveling_index():
    authorization = authorize("/settings/leveling")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        handle_settings(auth)
        handle_rewards(auth)
        handle_multipliers(auth)

    with engine.begin() as c:
        xp_per_message = setting_xp_per_message.get(c, auth["guild"])
        level_up_message = setting_level_up_message.get(c, auth["guild"]) == "true"
        level_up_message_text = setting_level_up_message_text.get(c, auth["guild"])
        xp_per_level = setting_xp_per_level.get(c, auth["guild"])

        reward_role_ids = [i.split(";") for i in setting_leveling_rewards.get(c, auth["guild"])] # id;level
        reward_roles = []
        for reward_role_i in range(len(reward_role_ids)):
            reward_role = reward_role_ids[reward_role_i]
            reward_role_name = c.execute(
                select(synced_roles.c.rname)
                .where((synced_roles.c.gid == auth["guild"]) & (synced_roles.c.rid == reward_role[0]))
            ).fetchone()

            reward_roles.append({
                "index": reward_role_i,
                "id": reward_role[0],
                "level": reward_role[1],
                "name": reward_role_name[0]
            })

        multiplier_ids = [i.split(";") for i in setting_leveling_multipliers.get(c, auth["guild"])] # start;end;multiplier
        multipliers = []
        for multiplier_i in range(len(multiplier_ids)):
            multiplier = multiplier_ids[multiplier_i]
            multipliers.append({
                "index": multiplier_i,
                "start": multiplier[0],
                "end": multiplier[1],
                "multiplier": multiplier[2]
            })

        roles = [{
            "id": i[0],
            "name": i[1]
        } for i in c.execute(
            select(synced_roles.c.rid, synced_roles.c.rname)
            .where(synced_roles.c.gid == auth["guild"])
        ).fetchall()]

    return render_template("leveling.html",
                           xp_per_message=xp_per_message, level_up_message=level_up_message, level_up_message_text=level_up_message_text,
                           xp_per_level=xp_per_level, reward_roles=reward_roles, multipliers=multipliers,
                           roles=roles)

@leveling_bp.route("/settings/leveling/edit/reward/<index>", methods=["GET", "POST"])
def edit_reward(index: str):
    if not index.isnumeric():
        return redirect("/settings/leveling", 302)

    authorization = authorize("/settings/leveling")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        reward_role_ids = [i.split(";") for i in setting_leveling_rewards.get(c, auth["guild"])] # id;level
        if len(reward_role_ids) <= int(index):
            return redirect("/settings/leveling")

        reward_role_id = reward_role_ids[int(index)]
        roles = [{
            "id": i[0],
            "name": i[1]
        } for i in c.execute(
            select(synced_roles.c.rid, synced_roles.c.rname)
            .where(synced_roles.c.gid == auth["guild"])
        ).fetchall()]

    if request.method == "POST":
        with engine.begin() as c:
            setting_leveling_rewards.remove_from_list(c, auth["guild"], ";".join(reward_role_ids[int(index)]))

            handle_rewards(auth, is_edit=True)
            return redirect("/settings/leveling", 303)

    return render_template("leveling_edit_reward.html",
                           selected_role=reward_role_id[0], index=index, level=reward_role_id[1], roles=roles)

@leveling_bp.route("/settings/leveling/delete/reward/<index>")
def remove_reward(index: str):
    if not index.isnumeric():
        return redirect("/settings/leveling", 302)

    authorization = authorize("/settings/leveling")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        reward_role_ids = [i.split(";") for i in setting_leveling_rewards.get(c, auth["guild"])] # id;level
        if len(reward_role_ids) <= int(index):
            return redirect("/settings/leveling")

        reward_role_id = reward_role_ids[int(index)]
        reward_role_name = c.execute(
            select(synced_roles.c.rname)
            .where((synced_roles.c.gid == auth["guild"]) & (synced_roles.c.rid == reward_role_id[0]))
        ).fetchone()

    if "confirm" in request.args and request.args["confirm"] == "yes":
        with engine.begin() as c:
            setting_leveling_rewards.remove_from_list(c, auth["guild"], ";".join(reward_role_ids[int(index)]))
            return redirect("/settings/leveling", 303)

    return render_template("leveling_remove_reward.html",
                           role_name=reward_role_name[0], index=index, level=reward_role_id[1])

@leveling_bp.route("/settings/leveling/edit/multiplier/<index>", methods=["GET", "POST"])
def edit_multiplier(index: str):
    if not index.isnumeric():
        return redirect("/settings/leveling", 302)

    authorization = authorize("/settings/leveling")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        multiplier_ids = [i.split(";") for i in setting_leveling_multipliers.get(c, auth["guild"])] # start;end;multiplier
        if len(multiplier_ids) <= int(index):
            return redirect("/settings/leveling", 302)

        multiplier = multiplier_ids[int(index)]

    if request.method == "POST":
        with engine.begin() as c:
            setting_leveling_multipliers.remove_from_list(c, auth["guild"], ";".join(multiplier_ids[int(index)]))

        handle_multipliers(auth)
        return redirect("/settings/leveling", 303)

    return render_template("leveling_edit_multiplier.html",
                           index=index, start_date=multiplier[0], end_date=multiplier[1], multiplier=multiplier[2])

@leveling_bp.route("/settings/leveling/delete/multiplier/<index>")
def delete_multiplier(index: str):
    if not index.isnumeric():
        return redirect("/settings/leveling", 302)

    authorization = authorize("/settings/leveling")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        multiplier_ids = [i.split(";") for i in setting_leveling_multipliers.get(c, auth["guild"])] # start;end;multiplier
        if len(multiplier_ids) <= int(index):
            return redirect("/settings/leveling", 302)

        multiplier = multiplier_ids[int(index)]

    if "confirm" in request.args and request.args["confirm"] == "yes":
        with engine.begin() as c:
            setting_leveling_multipliers.remove_from_list(c, auth["guild"], ";".join(multiplier_ids[int(index)]))

        return redirect("/settings/leveling", 303)

    return render_template("leveling_delete_multiplier.html",
                           start_date=multiplier[0], end_date=multiplier[1], multiplier=multiplier[2])