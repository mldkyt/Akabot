from dateparser.data.date_translation_data import sn
from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import delete, insert, select

from database import engine, roles_on_join, synced_roles
from utils.premium import get_limit
from web.webutils.discord_sync import validate_role_id
from web.webutils.tokens import authorize, get_token_data

roles_on_join_bp = Blueprint("roles_on_join", __name__)


def handle_add(auth):
    with engine.begin() as c:
        if "role" in request.form and validate_role_id(request.form["role"]):
            existing = c.execute(
                select(roles_on_join.c.rid).where(
                    (roles_on_join.c.gid == auth["guild"])
                    & (roles_on_join.c.rid == request.form["role"])
                )
            ).fetchone()
            if existing is not None:
                flash("Already present")
                return

            limit = get_limit(c, auth["guild"], 3)
            current = c.execute(
                select(roles_on_join.c.rid).where(roles_on_join.c.gid == auth["guild"])
            ).fetchall()
            if limit is not None and len(current) >= limit:
                flash("Free plan is limited to 3 roles on join")
                return

            c.execute(
                insert(roles_on_join).values(
                    gid=auth["guild"], rid=request.form["role"]
                )
            )
            flash("Added role on join")


def handle_delete(auth):
    with engine.begin() as c:
        c.execute(
            delete(roles_on_join).where(
                (roles_on_join.c.gid == auth["guild"])
                & (roles_on_join.c.rid == request.args["delete"])
            )
        )


@roles_on_join_bp.route("/settings/roles_on_join", methods=["GET", "POST"])
def roles_on_join_index():
    authorization = authorize("/settings/roles_on_join")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        handle_add(auth)

    if "delete" in request.args:
        handle_delete(auth)
        return redirect("/settings/roles_on_join", 302)

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
        "roles_on_join.html", roles_on_join=roles_on_join_list, roles=roles
    )
