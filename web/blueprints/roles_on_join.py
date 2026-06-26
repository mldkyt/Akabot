from dateparser.data.date_translation_data import sn
from flask import Blueprint, session, render_template, redirect, request, flash
from sqlalchemy import select

from database import engine, synced_roles
from utils.roles_on_join import setting_roles_on_join
from web.webutils.discord_sync import validate_role_id
from web.webutils.tokens import get_token_data, authorize

roles_on_join_bp = Blueprint("roles_on_join", __name__)

def handle_add(auth):
    with engine.begin() as c:
        if "role" in request.form and validate_role_id(request.form["role"]):
            if setting_roles_on_join.is_in_list(c, auth["guild"], request.form["role"]):
                flash("Already present")
                return

            setting_roles_on_join.add_to_list(c, auth["guild"], request.form["role"])
            flash("Added role on join")

@roles_on_join_bp.route("/settings/roles_on_join", methods=["GET", "POST"])
def roles_on_join_index():
    authorization = authorize("/settings/roles_on_join")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        handle_add(auth)

    with engine.begin() as c:
        roles_on_join_ids = setting_roles_on_join.get(c, auth["guild"])
        roles_on_join = []

        for i in range(len(roles_on_join_ids)):
            name = c.execute(
                select(synced_roles.c.rname)
                .where((synced_roles.c.gid == auth["guild"]) & (synced_roles.c.rid == roles_on_join_ids[i]))
            ).fetchone()
            if name is None:
                continue

            roles_on_join.append({
                "index": i,
                "id": roles_on_join_ids[i],
                "name": name[0]
            })

        roles = [{
            "id": i[0],
            "name": i[1]
        } for i in c.execute(
            select(synced_roles.c.rid, synced_roles.c.rname)
            .where(synced_roles.c.gid == auth["guild"])
        ).fetchall()]

    return render_template("roles_on_join.html", roles_on_join=roles_on_join, roles=roles)


@roles_on_join_bp.route("/settings/roles_on_join/delete/<index>")
def roles_on_join_delete(index: str):
    authorization = authorize("/settings/roles_on_join")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if not index.isnumeric():
        return redirect("/settings/roles_on_join", 302)

    with engine.begin() as c:
        roles_on_join_ids = setting_roles_on_join.get(c, auth["guild"])
        if len(roles_on_join_ids) <= int(index):
            return redirect("/settings/roles_on_join", 302)

        role_on_join_id = roles_on_join_ids[int(index)]

        role_on_join = c.execute(
            select(synced_roles.c.rname)
            .where((synced_roles.c.rid == role_on_join_id) & (synced_roles.c.gid == auth["guild"]))
        ).fetchone()
        if role_on_join is None:
            return redirect("/settings/roles_on_join", 302)

    if "confirm" in request.args and request.args["confirm"] == "yes":
        with engine.begin() as c:
            setting_roles_on_join.remove_from_list(c, auth["guild"], role_on_join_id)
            return redirect("/settings/roles_on_join", 302)

    return render_template("roles_on_join_delete.html", role_name=role_on_join[0], index=index)


