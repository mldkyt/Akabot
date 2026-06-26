from flask import Blueprint, session, render_template, redirect, request, flash
from sqlalchemy import select
from utils.temporary_vc import setting_temporary_vcs

from database import engine, synced_channels
from web.webutils.discord_sync import validate_voice_channel_id
from web.webutils.tokens import get_token_data, authorize

temporary_vcs_bp = Blueprint("temporary_vcs", __name__)

def handle_add(auth):
    with engine.begin() as c:
        if "channel" in request.form and validate_voice_channel_id(request.form["channel"]):
            if setting_temporary_vcs.is_in_list(c, auth["guild"], request.form["channel"]):
                flash("Already present")
                return

            setting_temporary_vcs.add_to_list(c, auth["guild"], request.form["channel"])
            flash("Added temporary VC creator channel")

@temporary_vcs_bp.route("/settings/temporary_vcs", methods=["GET", "POST"])
def temporary_vcs_index():
    authorization = authorize("/settings/temporary_vcs")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        handle_add(auth)

    with engine.begin() as c:
        temporary_vcs_ids = setting_temporary_vcs.get(c, auth["guild"])
        temporary_vcs = []

        for i in range(len(temporary_vcs_ids)):
            name = c.execute(
                select(synced_channels.c.cname)
                .where(synced_channels.c.cid == temporary_vcs_ids[i])
            ).fetchone()
            if name is None:
                flash(f"Failed to find channel {temporary_vcs_ids[i]}")
                continue

            temporary_vcs.append({
                "index": i,
                "id": temporary_vcs_ids[i],
                "name": name[0]
            })

        channels = [{
            "id": i[0],
            "name": i[1]
        } for i in c.execute(
            select(synced_channels.c.cid, synced_channels.c.cname)
            .where((synced_channels.c.gid == auth["guild"]) & (synced_channels.c.ctype == "voice"))
        ).fetchall()]

    return render_template("temporary_vcs.html", temporary_vcs=temporary_vcs, channels=channels)


@temporary_vcs_bp.route("/settings/temporary_vcs/delete/<index>")
def temporary_vcs_delete(index: str):
    authorization = authorize("/settings/temporary_vcs")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if not index.isnumeric():
        return redirect("/settings/temporary_vcs", 302)

    with engine.begin() as c:
        temporary_vcs_ids = setting_temporary_vcs.get(c, auth["guild"])
        if len(temporary_vcs_ids) <= int(index):
            return redirect("/settings/temporary_vcs", 302)

        temporary_vc_id = temporary_vcs_ids[int(index)]

        temporary_vc = c.execute(
            select(synced_channels.c.cname)
            .where((synced_channels.c.cid == temporary_vc_id) & (synced_channels.c.gid == auth["guild"]) & (synced_channels.c.ctype == "voice"))
        ).fetchone()
        if temporary_vc is None:
            return redirect("/settings/temporary_vcs", 302)

    if "confirm" in request.args and request.args["confirm"] == "yes":
        with engine.begin() as c:
            setting_temporary_vcs.remove_from_list(c, auth["guild"], temporary_vc_id)
            return redirect("/settings/temporary_vcs", 302)

    return render_template("temporary_vcs_delete.html", channel_name=temporary_vc[0], index=index)


