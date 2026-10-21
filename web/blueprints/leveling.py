import re
from datetime import datetime

from flask import Blueprint, session, render_template, request, flash, redirect
from sqlalchemy import delete, insert, select

from database import engine, leveling_multipliers, leveling_rewards, synced_roles
from logger import akabot_logger
from utils.leveling import setting_xp_per_message, setting_level_up_message, setting_level_up_message_text, \
    setting_xp_per_level
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
            setting_level_up_message.set(c, auth["guild"], "true")
        else:
            setting_level_up_message.set(c, auth["guild"], "false")

        level_up_message_text = request.form.get("level_up_message_text")

        if level_up_message_text:
            if 2 < len(level_up_message_text) < 250:
                setting_level_up_message_text.set(c, auth["guild"], level_up_message_text)
            else:
                flash("Invalid length of level up message text")

        xp_per_message = request.form.get("xp_per_message")
        if xp_per_message:
            if xp_per_message.isnumeric() and 1 <= int(xp_per_message) <= 100:
                setting_xp_per_message.set(c, auth["guild"], xp_per_message)
            else:
                flash("XP per message must be between 1 and 100")

        xp_per_level = request.form.get("xp_per_level")
        if xp_per_level:
            if xp_per_level.isnumeric() and 10 <= int(xp_per_level) <= 10000:
                setting_xp_per_level.set(c, auth["guild"], xp_per_level)
            else:
                flash("XP per level must be between 10 and 10000")

def handle_rewards(auth, is_edit: bool = False, remove_id: int | None = None) -> bool:
    reward_role = request.form.get("reward_role")
    required_level = request.form.get("required_level")

    if not reward_role or not required_level:
        return False

    if not validate_role_id(reward_role):
        flash("Role not found, try adding again if you just edited roles.")
        return False

    if not required_level.isnumeric() or not 1 <= int(required_level) <= 1000:
        flash("The level must be between 1 and 1000")
        return False

    with engine.begin() as c:
        if remove_id is not None:
            c.execute(
                delete(leveling_rewards).where(
                    (leveling_rewards.c.gid == auth["guild"])
                    & (leveling_rewards.c.id == remove_id)
                )
            )

        c.execute(
            insert(leveling_rewards).values(
                gid=auth["guild"], rid=reward_role, level=int(required_level)
            )
        )
        if is_edit:
            flash("Edited role reward successfully")
        else:
            flash("Added role reward successfully")

    return True

def handle_multipliers(auth, is_edit: bool = True, remove_id: int | None = None) -> bool:
    start = request.form.get("start")
    end = request.form.get("end")
    multiplier = request.form.get("multiplier")

    if not start or not end or not multiplier:
        return False
    if not multiplier.isnumeric():
        return False

    if not re.match(r"^(\d)+-(\d)+$", start):
        flash("Invalid format for start date for multiplier")
        return False

    start_month, start_day = start.split("-")

    try:
        datetime(2024, int(start_month), int(start_day))
    except Exception:
        akabot_logger.warning(
            f"Failed to parse start date {start_month}-{start_day} for leveling multiplier"
        )
        flash("Failed to parse start date")
        return False

    if not re.match(r"^(\d)+-(\d)+$", end):
        flash("Invalid format for end date for multiplier")
        return False

    end_month, end_day = end.split("-")

    try:
        datetime(2024, int(end_month), int(end_day))
    except Exception:
        akabot_logger.warning(
            f"Failed to parse end date {end_month}-{end_day} for leveling multiplier"
        )
        flash("Failed to parse end date")
        return False

    if not 1 <= int(multiplier) <= 1000:
        flash("Multiplier must be between 1 and 1000")
        return False

    with engine.begin() as c:
        if remove_id is not None:
            c.execute(
                delete(leveling_multipliers).where(
                    (leveling_multipliers.c.gid == auth["guild"])
                    & (leveling_multipliers.c.id == remove_id)
                )
            )

        c.execute(
            insert(leveling_multipliers).values(
                gid=auth["guild"],
                start_month=int(start_month),
                start_day=int(start_day),
                end_month=int(end_month),
                end_day=int(end_day),
                multiplier=int(multiplier),
            )
        )
        if is_edit:
            flash("Multiplier edited successfully")
        else:
            flash("Multiplier was created successfully")

    return True

def handle_delete(auth):
    with engine.begin() as c:
        if "delete_reward" in request.args:
            c.execute(
                delete(leveling_rewards).where(
                    (leveling_rewards.c.gid == auth["guild"])
                    & (leveling_rewards.c.id == request.args["delete_reward"])
                )
            )
            return True

        if "delete_multiplier" in request.args:
            c.execute(
                delete(leveling_multipliers).where(
                    (leveling_multipliers.c.gid == auth["guild"])
                    & (leveling_multipliers.c.id == request.args["delete_multiplier"])
                )
            )
            return True

    return False


@leveling_bp.route('/settings/leveling', methods=["GET", "POST"])
def leveling_index():
    authorization = authorize("/settings/leveling")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        section = request.form.get("_section", "general")
        if section == "general":
            handle_settings(auth)
            return redirect("/settings/leveling?tab=general", 303)

        action = request.form.get("action", "create")
        item_id = request.form.get("id", "")
        if section == "rewards":
            if action == "create":
                handle_rewards(auth)
            elif action == "update" and item_id.isnumeric():
                handle_rewards(auth, is_edit=True, remove_id=int(item_id))
            elif action == "delete" and item_id.isnumeric():
                with engine.begin() as c:
                    c.execute(
                        delete(leveling_rewards).where(
                            (leveling_rewards.c.gid == auth["guild"])
                            & (leveling_rewards.c.id == int(item_id))
                        )
                    )
                flash("Deleted role reward")
            return redirect("/settings/leveling?tab=rewards", 303)

        if section == "multipliers":
            if action == "create":
                handle_multipliers(auth, is_edit=False)
            elif action == "update" and item_id.isnumeric():
                handle_multipliers(auth, is_edit=True, remove_id=int(item_id))
            elif action == "delete" and item_id.isnumeric():
                with engine.begin() as c:
                    c.execute(
                        delete(leveling_multipliers).where(
                            (leveling_multipliers.c.gid == auth["guild"])
                            & (leveling_multipliers.c.id == int(item_id))
                        )
                    )
                flash("Deleted multiplier")
            return redirect("/settings/leveling?tab=multipliers", 303)

    active_tab = request.args.get("tab", "general")
    if active_tab not in {"general", "rewards", "multipliers"}:
        active_tab = "general"

    with engine.begin() as c:
        xp_per_message = setting_xp_per_message.get(c, auth["guild"])
        level_up_message = setting_level_up_message.get(c, auth["guild"]) == "true"
        level_up_message_text = setting_level_up_message_text.get(c, auth["guild"])
        xp_per_level = setting_xp_per_level.get(c, auth["guild"])

        reward_rows = c.execute(
            select(leveling_rewards.c.id, leveling_rewards.c.rid, leveling_rewards.c.level)
            .where(leveling_rewards.c.gid == auth["guild"])
            .order_by(leveling_rewards.c.id)
        ).fetchall()
        reward_roles = []
        for reward_role_i in range(len(reward_rows)):
            reward_role = reward_rows[reward_role_i]
            reward_role_name = c.execute(
                select(synced_roles.c.rname)
                .where((synced_roles.c.gid == auth["guild"]) & (synced_roles.c.rid == reward_role[1]))
            ).fetchone()

            reward_roles.append({
                "index": reward_role_i,
                "id": reward_role[0],
                "rid": reward_role[1],
                "level": reward_role[2],
                "name": reward_role_name[0] if reward_role_name else "Unknown role"
            })

        multiplier_rows = c.execute(
            select(
                leveling_multipliers.c.start_month,
                leveling_multipliers.c.start_day,
                leveling_multipliers.c.end_month,
                leveling_multipliers.c.end_day,
                leveling_multipliers.c.multiplier,
                leveling_multipliers.c.id,
            )
            .where(leveling_multipliers.c.gid == auth["guild"])
            .order_by(leveling_multipliers.c.id)
        ).fetchall()
        multipliers = []
        for multiplier_i in range(len(multiplier_rows)):
            multiplier = multiplier_rows[multiplier_i]
            multipliers.append({
                "index": multiplier_i,
                "id": multiplier[5],
                "start": f"{multiplier[0]:02}-{multiplier[1]:02}",
                "end": f"{multiplier[2]:02}-{multiplier[3]:02}",
                "multiplier": str(multiplier[4])
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
                           roles=roles, active_tab=active_tab)
