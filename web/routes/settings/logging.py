from flask import Blueprint, render_template, session, request, flash
from sqlalchemy import select

from database import engine, synced_channels
from utils.logs import logging_channel, logging_settings
from web.webutils.discord_sync import validate_text_channel_id
from web.webutils.tokens import get_token_data, authorize

logging_bp = Blueprint("logging", __name__)

def handle_saving_settings(auth):
    with engine.begin() as c:
        if "logging_channel" in request.form:
            if request.form["logging_channel"] == "unset":
                logging_channel.direct_set(c, auth["guild"], "")
            elif validate_text_channel_id(request.form["logging_channel"]):
                logging_channel.direct_set(c, auth["guild"], request.form["logging_channel"])
            else:
                flash("Invalid logging channel, not changing setting")

        for setting in logging_settings:
            if request.form.get(setting[0]):
                setting[1].direct_set(c, auth["guild"], "true")
            else:
                setting[1].direct_set(c, auth["guild"], "false")

@logging_bp.route("/settings/logging", methods=["GET", "POST"])
def logging_index():
    authorization = authorize("/settings")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        handle_saving_settings(auth)

    settings = []
    with engine.begin() as c:
        logging_channel_id = logging_channel.get(c, auth["guild"])

        channels = [{
            "id": i[0],
            "name": i[1]
        } for i in c.execute(
            select(synced_channels.c.cid, synced_channels.c.cname)
            .where((synced_channels.c.gid == auth["guild"]) & (synced_channels.c.ctype == "text"))
        ).fetchall()]

        for setting in logging_settings:
            settings.append({
                "key": setting[0],
                "name": setting[1].name.split(":")[1].strip(),
                "value": setting[1].get(c, auth["guild"]) == "true"
            })

    return render_template("logging.html",
                           logging_channel=logging_channel_id, channels=channels,
                           logging_settings=settings)
