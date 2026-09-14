from flask import Blueprint, session, render_template, request, flash, redirect
from sqlalchemy import select

from database import engine, synced_channels
from utils.premium import get_limit, get_premium_context
from utils.statistic_channels import setting_statistic_channels
from web.webutils.discord_sync import validate_voice_channel_id
from web.webutils.tokens import authorize, get_token_data

statistic_channels_bp = Blueprint("statistic_channels", __name__)

def handle_post(auth, is_edit: bool = False):
    if "channel" not in request.form or "template" not in request.form:
        return
    if not validate_voice_channel_id(request.form["channel"]):
        flash("Invalid voice channel selected")
        return
    if 2 > len(request.form["template"]) > 50:
        flash("Template too short or too long, keep it between 2 and 50 characters")
        return
    if ";" in request.form["template"]:
        flash("The template must not have semicolons")
        return

    with engine.begin() as c:
        statistic_channels_ids = [i.split(";")[0] for i in setting_statistic_channels.get(c, auth["guild"])]
        if request.form["channel"] in statistic_channels_ids:
            flash("This ID already has a template assigned, please edit instead!")
            return

        limit = get_limit(c, auth["guild"], 2)
        if limit is not None and len(statistic_channels_ids) >= limit:
            flash("Free plan is limited to 2 statistic channels")
            return

        setting_statistic_channels.add_to_list(c, auth["guild"], f"{request.form['channel']};{request.form['template']}")

@statistic_channels_bp.route("/settings/statistic_channels", methods=["GET", "POST"])
def statistic_channels_index():
    authorization = authorize("/settings/statistic_channels")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        handle_post(auth)

    with engine.begin() as c:
        statistic_channels_1 = setting_statistic_channels.get(c, auth["guild"])
        statistic_channels = []
        for i in range(len(statistic_channels_1)):
            args = statistic_channels_1[i].split(";")
            channel_name = c.execute(
                select(synced_channels.c.cname)
                .where((synced_channels.c.cid == args[0]) & (synced_channels.c.gid == auth["guild"]))
            ).fetchone()

            if channel_name is None:
                continue

            statistic_channels.append({
                "index": i,
                "id": args[0],
                "name": channel_name[0],
                "template": args[1]
            })

        channels = [{
            "id": i[0],
            "name": i[1]
        } for i in c.execute(
            select(synced_channels.c.cid, synced_channels.c.cname)
            .where((synced_channels.c.gid == auth["guild"]) & (synced_channels.c.ctype == "voice"))
        ).fetchall()]

    return render_template("statistic_channels.html", statistic_channels=statistic_channels, channels=channels)

@statistic_channels_bp.route("/settings/statistic_channels/edit/<index>", methods=["POST"])
def statistic_channels_edit(index: str):
    authorization = authorize("/settings/statistic_channels")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if not index.isnumeric():
        return redirect("/settings/statistic_channels", 303)

    with engine.begin() as c:
        statistic_channels_1 = setting_statistic_channels.get(c, auth["guild"])
        if len(statistic_channels_1) <= int(index):
            return redirect("/settings/statistic_channels", 303)

        setting_statistic_channels.remove_from_list(c, auth["guild"], statistic_channels_1[int(index)])
        handle_post(auth, is_edit=True)
        return redirect("/settings/statistic_channels", 303)



@statistic_channels_bp.route("/settings/statistic_channels/delete/<index>")
def statistic_channels_delete(index: str):
    authorization = authorize("/settings/statistic_channels")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if not index.isnumeric():
        return redirect("/settings/statistic_channels", 302)

    with engine.begin() as c:
        statistic_channels_ids = setting_statistic_channels.get(c, auth["guild"])
        if len(statistic_channels_ids) <= int(index):
            return redirect("/settings/statistic_channels", 302)

        statistic_channel_id = statistic_channels_ids[int(index)]

        statistic_channel = c.execute(
            select(synced_channels.c.cname)
            .where((synced_channels.c.cid == statistic_channel_id.split(";")[0]) & (synced_channels.c.gid == auth["guild"]))
        ).fetchone()
        if statistic_channel is None:
            return redirect("/settings/statistic_channels", 302)

    if "confirm" in request.args and request.args["confirm"] == "yes":
        with engine.begin() as c:
            setting_statistic_channels.remove_from_list(c, auth["guild"], statistic_channel_id)
            return redirect("/settings/statistic_channels", 302)

    return render_template("statistic_channels_delete.html", channel_name=statistic_channel[0], index=index)


