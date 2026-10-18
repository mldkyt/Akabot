from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import delete, insert, select

from database import engine, moderator_roles, synced_roles
from web.webutils.discord_sync import validate_role_id
from web.webutils.tokens import authorize, get_token_data

moderation_bp = Blueprint("moderation", __name__)


def handle_add(auth):
    with engine.begin() as c:
        if "role" in request.form and validate_role_id(request.form["role"]):
            existing = c.execute(
                select(moderator_roles.c.rid).where(
                    (moderator_roles.c.gid == auth["guild"])
                    & (moderator_roles.c.rid == request.form["role"])
                )
            ).fetchone()
            if existing is not None:
                flash("Already present")
                return

            c.execute(
                insert(moderator_roles).values(
                    gid=auth["guild"], rid=request.form["role"]
                )
            )
            flash("Added moderation role")


def handle_delete(auth):
    with engine.begin() as c:
        c.execute(
            delete(moderator_roles).where(
                (moderator_roles.c.gid == auth["guild"])
                & (moderator_roles.c.rid == request.args["delete"])
            )
        )


@moderation_bp.route("/settings/moderation", methods=["GET", "POST"])
def moderation_index():
    authorization = authorize("/settings/moderation")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        handle_add(auth)

        return redirect("/settings/moderation", 303)

    if "delete" in request.args:
        handle_delete(auth)
        return redirect("/settings/moderation", 302)

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
        "moderation.html", roles=roles, moderator_roles=the_roles
    )

@moderation_bp.route("/settings/moderation/delete/<index>")
def moderation_delete(index: str):
    authorization = authorize("/settings/moderation")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if not index.isnumeric():
        return redirect("/settings/moderation", 302)

    with engine.begin() as c:
        the_roles_ids = [
            i[0]
            for i in c.execute(
                select(moderator_roles.c.rid)
                .where(moderator_roles.c.gid == auth["guild"])
                .order_by(moderator_roles.c.id)
            ).fetchall()
        ]
        if len(the_roles_ids) <= int(index):
            return redirect("/settings/moderation", 302)

        the_role_id = the_roles_ids[int(index)]

        the_role = c.execute(
            select(synced_roles.c.rname).where(
                (synced_roles.c.rid == the_role_id)
                & (synced_roles.c.gid == auth["guild"])
            )
        ).fetchone()
        if the_role is None:
            return redirect("/settings/moderation", 302)

    if "confirm" in request.args and request.args["confirm"] == "yes":
        with engine.begin() as c:
            c.execute(
                delete(moderator_roles).where(
                    (moderator_roles.c.gid == auth["guild"])
                    & (moderator_roles.c.rid == the_role_id)
                )
            )
            return redirect("/settings/moderation", 302)

    return render_template("moderation_delete.html", role_name=the_role[0], index=index)
