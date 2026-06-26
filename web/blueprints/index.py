from flask import Blueprint, render_template, session, request, flash
from sqlalchemy import select

from database import engine, synced_channels
from utils.bot_channel import setting_bot_channel
from web.webutils.discord_sync import validate_text_channel_id
from web.webutils.tokens import authorize, get_token_data

settings_index_bp = Blueprint("settings_index", __name__, template_folder='templates')


def save_settings(auth):
    if request.method != "POST":
        return

    # Bot channel
    if "botchannel" in request.form:
        if request.form["botchannel"] == "unset":
            with engine.begin() as c:
                setting_bot_channel.set(c, auth["guild"], "")
        elif validate_text_channel_id(request.form["botchannel"]):
            with engine.begin() as c:
                setting_bot_channel.set(c, auth["guild"], request.form["botchannel"])
        else:
            flash("Bot channel property found but the value was invalid.")


@settings_index_bp.route("/settings", methods=["GET", "POST"])
def settings_index():
    authorization = authorize("/settings")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    save_settings(auth)

    with engine.begin() as c:
        bot_chan = setting_bot_channel.get(c, auth["guild"])
        text_channels = [{
            "id": i[0],
            "name": i[1]
        } for i in c.execute(
            select(synced_channels.c.cid, synced_channels.c.cname)
            .where((synced_channels.c.gid == str(auth["guild"])) & (synced_channels.c.ctype == "text"))
        )]

    return render_template("index.html", current_bot_channel=bot_chan, text_channels=text_channels)
