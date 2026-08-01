from idlelib.rpc import request_queue

from flask import Blueprint, session, render_template, request, flash
from sqlalchemy import select

from database import engine, synced_roles, synced_channels
from utils.verification import setting_verification_role, setting_verification_mode, introduction_channel
from web.webutils.discord_sync import validate_role_id, validate_text_channel_id
from web.webutils.tokens import authorize, get_token_data

verification_bp = Blueprint("verification_settings", __name__, template_folder='templates')

def handle_save(auth):
    with engine.begin() as c:
        if "verification_role" in request.form:
            if request.form["verification_role"] == "unset":
                setting_verification_role.set(c, auth["guild"], "")
            elif validate_role_id(request.form["verification_role"]):
                setting_verification_role.set(c, auth["guild"], request.form["verification_role"])

        if "verification_mode" in request.form and request.form["verification_mode"] in ["none", "math", "silly"]:
            setting_verification_mode.set(c, auth["guild"], request.form["verification_mode"])

        # Introduction channel
        if "introductionchannel" in request.form:
            if request.form["introductionchannel"] == "unset":
                with engine.begin() as c:
                    introduction_channel.set(c, auth["guild"], "")
            elif validate_text_channel_id(request.form["introductionchannel"]):
                with engine.begin() as c:
                    introduction_channel.set(c, auth["guild"], request.form["introductionchannel"])
            else:
                flash("Admin bot channel property found but the value was invalid.")

@verification_bp.route("/settings/verification", methods=["GET", "POST"])
def verification_index():
    authorization = authorize("/settings/verification")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        handle_save(auth)

    with engine.begin() as c:
        verification_role_id = setting_verification_role.get(c, auth["guild"])
        verification_mode = setting_verification_mode.get(c, auth["guild"])
        introduction_channel_id = introduction_channel.get(c, auth["guild"])

        roles = [{
            "id": i[0],
            "name": i[1]
        } for i in c.execute(
            select(synced_roles.c.rid, synced_roles.c.rname)
            .where(synced_roles.c.gid == auth["guild"])
        ).fetchall()]

        text_channels = [{
            "id": i[0],
            "name": i[1]
        } for i in c.execute(
            select(synced_channels.c.cid, synced_channels.c.cname)
            .where((synced_channels.c.gid == str(auth["guild"])) & (synced_channels.c.ctype == "text"))
        )]

    return render_template("verification.html", verification_role=verification_role_id,
                           verification_mode=verification_mode, roles=roles, text_channels=text_channels,
                           introduction_channel=introduction_channel_id)
