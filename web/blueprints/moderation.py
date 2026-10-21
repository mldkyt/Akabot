from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import delete, insert, select, update

from database import engine, moderator_roles, synced_roles
from web.webutils.tokens import authorize, get_token_data

moderation_bp = Blueprint("moderation", __name__, template_folder="templates")


@moderation_bp.route("/settings/moderation", methods=["GET", "POST"])
def moderation_index():
    authorization = authorize("/settings/moderation")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        section = request.form.get("_section", "roles")
        action = request.form.get("action", "create")

        if section == "roles":
            role_id = request.form.get("role", "")
            old_role_id = request.form.get("id", "")

            with engine.begin() as c:
                role = c.execute(
                    select(synced_roles.c.rid).where(
                        (synced_roles.c.gid == auth["guild"])
                        & (synced_roles.c.rid == role_id)
                    )
                ).fetchone()

                if action == "create":
                    if role is None:
                        flash("Unknown role")
                    else:
                        existing = c.execute(
                            select(moderator_roles.c.rid).where(
                                (moderator_roles.c.gid == auth["guild"])
                                & (moderator_roles.c.rid == role_id)
                            )
                        ).fetchone()
                        if existing is not None:
                            flash("Already present")
                        else:
                            c.execute(
                                insert(moderator_roles).values(
                                    gid=auth["guild"], rid=role_id
                                )
                            )
                            flash("Added moderation role")
                elif action == "update" and old_role_id:
                    if role is None:
                        flash("Unknown role")
                    else:
                        existing = c.execute(
                            select(moderator_roles.c.rid).where(
                                (moderator_roles.c.gid == auth["guild"])
                                & (moderator_roles.c.rid == role_id)
                            )
                        ).fetchone()
                        if existing is not None and role_id != old_role_id:
                            flash("Already present")
                        else:
                            c.execute(
                                update(moderator_roles)
                                .where(
                                    (moderator_roles.c.gid == auth["guild"])
                                    & (moderator_roles.c.rid == old_role_id)
                                )
                                .values(rid=role_id)
                            )
                            flash("Saved moderation role")
                elif action == "delete" and old_role_id:
                    c.execute(
                        delete(moderator_roles).where(
                            (moderator_roles.c.gid == auth["guild"])
                            & (moderator_roles.c.rid == old_role_id)
                        )
                    )
                    flash("Deleted moderation role")

        return redirect(
            f"/settings/moderation?tab={request.form.get('_tab', 'roles')}", 303
        )

    active_tab = request.args.get("tab", "general")
    if active_tab not in {"general", "roles"}:
        active_tab = "general"

    with engine.begin() as c:
        the_roles_ids = [
            i[0]
            for i in c.execute(
                select(moderator_roles.c.rid)
                .where(moderator_roles.c.gid == auth["guild"])
                .order_by(moderator_roles.c.id)
            ).fetchall()
        ]
        the_roles = []

        for role in range(len(the_roles_ids)):
            role_name = c.execute(
                select(synced_roles.c.rname).where(
                    (synced_roles.c.gid == auth["guild"])
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
                    synced_roles.c.gid == auth["guild"]
                )
            ).fetchall()
        ]

    return render_template(
        "moderation.html",
        roles=roles,
        moderator_roles=the_roles,
        active_tab=active_tab,
    )
