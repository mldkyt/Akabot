from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import delete, insert, select, update

from database import (
    engine,
    moderator_roles,
    moderator_warning_actions,
    moderator_warnings,
    synced_roles,
)
from utils.moderation import settings_moderator_warnings_expiry
from web.webutils.tokens import authorize, get_token_data

moderation_bp = Blueprint("moderation", __name__, template_folder="templates")

WARNING_ACTION_TYPES = ("kick", "ban", "timeout")
MAX_WARNING_COUNT = 1000
MAX_TIMEOUT_DAYS = 28
MAX_EXPIRY_DAYS = 3650
TABS = {"general", "roles", "warning_actions"}


def _handle_roles_post(c, guild_id: str):
    action = request.form.get("action", "create")
    role_id = request.form.get("role", "")
    old_role_id = request.form.get("id", "")

    role = c.execute(
        select(synced_roles.c.rid).where(
            (synced_roles.c.gid == guild_id)
            & (synced_roles.c.rid == role_id)
        )
    ).fetchone()

    if action == "create":
        if role is None:
            flash("Unknown role")
        else:
            existing = c.execute(
                select(moderator_roles.c.rid).where(
                    (moderator_roles.c.gid == guild_id)
                    & (moderator_roles.c.rid == role_id)
                )
            ).fetchone()
            if existing is not None:
                flash("Already present")
            else:
                c.execute(
                    insert(moderator_roles).values(gid=guild_id, rid=role_id)
                )
                flash("Added moderation role")
    elif action == "update" and old_role_id:
        if role is None:
            flash("Unknown role")
        else:
            existing = c.execute(
                select(moderator_roles.c.rid).where(
                    (moderator_roles.c.gid == guild_id)
                    & (moderator_roles.c.rid == role_id)
                )
            ).fetchone()
            if existing is not None and role_id != old_role_id:
                flash("Already present")
            else:
                c.execute(
                    update(moderator_roles)
                    .where(
                        (moderator_roles.c.gid == guild_id)
                        & (moderator_roles.c.rid == old_role_id)
                    )
                    .values(rid=role_id)
                )
                flash("Saved moderation role")
    elif action == "delete" and old_role_id:
        c.execute(
            delete(moderator_roles).where(
                (moderator_roles.c.gid == guild_id)
                & (moderator_roles.c.rid == old_role_id)
            )
        )
        flash("Deleted moderation role")


def _handle_general_post(c, guild_id: str):
    value = request.form.get("warnings_expiry", "")
    if not value.isnumeric() or not 0 <= int(value) <= MAX_EXPIRY_DAYS:
        flash("Invalid warning expiry value")
        return

    settings_moderator_warnings_expiry.set(c, guild_id, value)
    flash("Saved warning settings")


def _parse_warning_action_form() -> dict | None:
    action = request.form.get("type", "")
    warning_count = request.form.get("warning_count", "")
    parameter = request.form.get("parameter", "").strip()

    if action not in WARNING_ACTION_TYPES:
        flash("Invalid warning action")
        return None

    if not warning_count.isnumeric() or not 1 <= int(warning_count) <= MAX_WARNING_COUNT:
        flash("Invalid warning count")
        return None

    if action == "timeout":
        if not parameter.isnumeric() or not 1 <= int(parameter) <= MAX_TIMEOUT_DAYS:
            flash("Invalid timeout duration (days)")
            return None
    else:
        parameter = None

    return {
        "action": action,
        "warning_count": int(warning_count),
        "parameter": parameter,
    }


def _handle_warning_actions_post(c, guild_id: str):
    form_action = request.form.get("action", "create")

    if form_action == "create":
        values = _parse_warning_action_form()
        if values is None:
            return

        existing = c.execute(
            select(moderator_warning_actions.c.id).where(
                (moderator_warning_actions.c.gid == guild_id)
                & (moderator_warning_actions.c.action == values["action"])
                & (
                    moderator_warning_actions.c.warning_count
                    == values["warning_count"]
                )
            )
        ).fetchone()
        if existing is not None:
            flash("A warning action for this action and warning count already exists")
            return

        c.execute(
            insert(moderator_warning_actions).values(gid=guild_id, **values)
        )
        flash("Added warning action")
        return

    action_id = request.form.get("id", "")
    if not action_id.isnumeric():
        flash("Invalid warning action id")
        return

    action_id = int(action_id)

    if form_action == "delete":
        c.execute(
            delete(moderator_warning_actions).where(
                (moderator_warning_actions.c.id == action_id)
                & (moderator_warning_actions.c.gid == guild_id)
            )
        )
        flash("Deleted warning action")
        return

    if form_action != "update":
        flash("Invalid warning action")
        return

    values = _parse_warning_action_form()
    if values is None:
        return

    existing = c.execute(
        select(moderator_warning_actions.c.id).where(
            (moderator_warning_actions.c.gid == guild_id)
            & (moderator_warning_actions.c.action == values["action"])
            & (
                moderator_warning_actions.c.warning_count
                == values["warning_count"]
            )
            & (moderator_warning_actions.c.id != action_id)
        )
    ).fetchone()
    if existing is not None:
        flash("A warning action for this action and warning count already exists")
        return

    c.execute(
        update(moderator_warning_actions)
        .where(
            (moderator_warning_actions.c.id == action_id)
            & (moderator_warning_actions.c.gid == guild_id)
        )
        .values(**values)
    )
    flash("Saved warning action")


def _handle_warnings_post(c, guild_id: str):
    warning_id = request.form.get("id", "")
    if request.form.get("action") != "delete" or not warning_id.isnumeric():
        flash("Invalid warning")
        return

    c.execute(
        delete(moderator_warnings).where(
            (moderator_warnings.c.id == int(warning_id))
            & (moderator_warnings.c.gid == guild_id)
        )
    )
    flash("Deleted warning")


@moderation_bp.route("/settings/moderation", methods=["GET", "POST"])
def moderation_index():
    authorization = authorize("/settings/moderation")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None
    guild_id = auth["guild"]

    if request.method == "POST":
        section = request.form.get("_section", "general")
        active_tab = request.form.get("_tab", section)
        if active_tab not in TABS:
            active_tab = "general"

        with engine.begin() as c:
            if section == "general":
                _handle_general_post(c, guild_id)
            elif section == "roles":
                _handle_roles_post(c, guild_id)
            elif section == "warning_actions":
                _handle_warning_actions_post(c, guild_id)

        return redirect(f"/settings/moderation?tab={active_tab}", 303)

    active_tab = request.args.get("tab", "general")
    if active_tab not in TABS:
        active_tab = "general"

    with engine.begin() as c:
        warnings_expiry = settings_moderator_warnings_expiry.get(c, guild_id)

        warning_actions = [
            {
                "id": i[0],
                "action": i[1],
                "warning_count": i[2],
                "parameter": i[3],
            }
            for i in c.execute(
                select(
                    moderator_warning_actions.c.id,
                    moderator_warning_actions.c.action,
                    moderator_warning_actions.c.warning_count,
                    moderator_warning_actions.c.parameter,
                )
                .where(moderator_warning_actions.c.gid == guild_id)
                .order_by(
                    moderator_warning_actions.c.warning_count,
                    moderator_warning_actions.c.id,
                )
            ).fetchall()
        ]

        the_roles_ids = [
            i[0]
            for i in c.execute(
                select(moderator_roles.c.rid)
                .where(moderator_roles.c.gid == guild_id)
                .order_by(moderator_roles.c.id)
            ).fetchall()
        ]
        the_roles = []

        for role in range(len(the_roles_ids)):
            role_name = c.execute(
                select(synced_roles.c.rname).where(
                    (synced_roles.c.gid == guild_id)
                    & (synced_roles.c.rid == the_roles_ids[role])
                )
            ).fetchone()

            if role_name is None:
                continue

            the_roles.append(
                {"index": role, "id": the_roles_ids[role], "name": role_name[0]}
            )

        roles = [
            {"id": i[0], "name": i[1]}
            for i in c.execute(
                select(synced_roles.c.rid, synced_roles.c.rname).where(
                    synced_roles.c.gid == guild_id
                )
            ).fetchall()
        ]

    return render_template(
        "moderation.html",
        roles=roles,
        moderator_roles=the_roles,
        warning_actions=warning_actions,
        warnings_expiry=warnings_expiry,
        active_tab=active_tab,
    )
