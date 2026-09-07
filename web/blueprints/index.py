from flask import Blueprint, flash, render_template, request, session
from sqlalchemy import select

from database import engine, synced_channels
from utils.bot_channel import setting_admin_bot_channel, setting_bot_channel
from utils.chat_streaks import server_message_delay, server_response_setting
from web.webutils.discord_sync import validate_text_channel_id
from web.webutils.tokens import authorize, get_token_data

settings_index_bp = Blueprint("settings_index", __name__, template_folder="templates")


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

    # Admin bot channel
    if "adminbotchannel" in request.form:
        if request.form["adminbotchannel"] == "unset":
            with engine.begin() as c:
                setting_admin_bot_channel.set(c, auth["guild"], "")
        elif validate_text_channel_id(request.form["adminbotchannel"]):
            with engine.begin() as c:
                setting_admin_bot_channel.set(
                    c, auth["guild"], request.form["adminbotchannel"]
                )
        else:
            flash("Admin bot channel property found but the value was invalid.")

    # Response setting
    if "response" in request.form:
        if request.form["response"] in ["on", "bot", "bot_noping", "off"]:
            with engine.begin() as c:
                server_response_setting.set(c, auth["guild"], request.form["response"])
        else:
            flash(f"Invalid value {request.form['response']} for bot response setting")

    if "responsedelete" in request.form:
        if (
            request.form["responsedelete"].isnumeric()
            and 2 < int(request.form["responsedelete"]) < 60
        ):
            with engine.begin() as c:
                server_message_delay.set(
                    c, auth["guild"], request.form["responsedelete"]
                )
        else:
            flash(
                f"Invalid value {request.form['responsedelete']} for response delete delay. Must be between 2 seconds and 60 seconds."
            )


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
        admin_bot_chan = setting_admin_bot_channel.get(c, auth["guild"])
        text_channels = [
            {"id": i[0], "name": i[1]}
            for i in c.execute(
                select(synced_channels.c.cid, synced_channels.c.cname).where(
                    (synced_channels.c.gid == str(auth["guild"]))
                    & (synced_channels.c.ctype == "text")
                )
            )
        ]

        response = server_response_setting.get(c, auth["guild"])
        response_delete_delay = server_message_delay.get(c, auth["guild"])

    return render_template(
        "index.html",
        current_bot_channel=bot_chan,
        current_admin_bot_channel=admin_bot_chan,
        text_channels=text_channels,
        response=response,
        response_delete_delay=response_delete_delay,
    )
