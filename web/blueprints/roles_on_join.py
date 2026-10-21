from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import delete, insert, select, update

from database import engine, roles_on_join, synced_roles
from web.webutils.tokens import authorize, get_token_data

roles_on_join_bp = Blueprint("roles_on_join", __name__, template_folder="templates")


@roles_on_join_bp.route("/settings/roles_on_join", methods=["GET", "POST"])
def roles_on_join_index():
    authorization = authorize("/settings/roles_on_join")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        section = request.form.get("_section", "roles")
        action = request.form.get("action", "create")
        role_id = request.form.get("role", "")
        old_role_id = request.form.get("id", "")

        if section == "roles":
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
                            select(roles_on_join.c.rid).where(
                                (roles_on_join.c.gid == auth["guild"])
                                & (roles_on_join.c.rid == role_id)
                            )
                        ).fetchone()
                        if existing is not None:
                            flash("Already present")
                        else:
                            c.execute(
                                insert(roles_on_join).values(
                                    gid=auth["guild"], rid=role_id
                                )
                            )
                            flash("Added role on join")
                elif action == "update" and old_role_id:
                    if role is None:
                        flash("Unknown role")
                    else:
                        existing = c.execute(
                            select(roles_on_join.c.rid).where(
                                (roles_on_join.c.gid == auth["guild"])
                                & (roles_on_join.c.rid == role_id)
                            )
                        ).fetchone()
                        if existing is not None and role_id != old_role_id:
                            flash("Already present")
                        else:
                            c.execute(
                                update(roles_on_join)
                                .where(
                                    (roles_on_join.c.gid == auth["guild"])
                                    & (roles_on_join.c.rid == old_role_id)
                                )
                                .values(rid=role_id)
                            )
                            flash("Saved role on join")
                elif action == "delete" and old_role_id:
                    c.execute(
                        delete(roles_on_join).where(
                            (roles_on_join.c.gid == auth["guild"])
                            & (roles_on_join.c.rid == old_role_id)
                        )
                    )
                    flash("Deleted role on join")

        return redirect(
            f"/settings/roles_on_join?tab={request.form.get('_tab', 'roles')}", 303
        )

    active_tab = request.args.get("tab", "general")
    if active_tab not in {"general", "roles"}:
        active_tab = "general"

    with engine.begin() as c:
        roles_on_join_ids = [
            i[0]
            for i in c.execute(
                select(roles_on_join.c.rid)
                .where(roles_on_join.c.gid == auth["guild"])
                .order_by(roles_on_join.c.id)
            ).fetchall()
        ]
        roles_on_join_list = []

        for i in range(len(roles_on_join_ids)):
            name = c.execute(
                select(synced_roles.c.rname).where(
                    (synced_roles.c.gid == auth["guild"])
                    & (synced_roles.c.rid == roles_on_join_ids[i])
                )
            ).fetchone()
            if name is None:
                continue

            roles_on_join_list.append(
                {"index": i, "id": roles_on_join_ids[i], "name": name[0]}
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
        "roles_on_join.html",
        roles_on_join=roles_on_join_list,
        roles=roles,
        active_tab=active_tab,
    )
