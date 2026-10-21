from flask import Blueprint, session, render_template, request, flash
from sqlalchemy import select

from database import engine, synced_channels
from utils.welcome_goodbye import welcome_message_title, welcome_message_message, welcome_message_type, \
    welcome_grace_period_first, welcome_grace_period_second, goodbye_message_title, goodbye_message_message, \
    goodbye_message_type, welcome_channel, goodbye_channel
from web.webutils.discord_sync import validate_text_channel_id
from web.webutils.tokens import authorize, get_token_data

welcome_goodbye_bp = Blueprint("welcome_goodbye", __name__, template_folder="templates")

def handle_save(auth):
    with engine.begin() as c:
        if "welcome_channel" in request.form:
            if request.form["welcome_channel"] == "unset":
                welcome_channel.set(c, auth["guild"], "")
            elif validate_text_channel_id(request.form["welcome_channel"]):
                welcome_channel.set(c, auth["guild"], request.form["welcome_channel"])

        if "welcome_title" in request.form and 1 < len(request.form["welcome_title"]) < 100:
            welcome_message_title.set(c, auth["guild"], request.form["welcome_title"])

        if "welcome_msg" in request.form and 1 < len(request.form["welcome_msg"]) < 1000:
            welcome_message_message.set(c, auth["guild"], request.form["welcome_msg"])
            
        if "welcome_type" in request.form and request.form["welcome_type"] in ["text", "embed"]:
            welcome_message_type.set(c, auth["guild"], request.form["welcome_type"])
        
        if "welcome_first" in request.form and request.form["welcome_first"].isnumeric() and \
            0 < int(request.form["welcome_first"]) < 300:
            welcome_grace_period_first.set(c, auth["guild"], request.form["welcome_first"])
            
        if "welcome_second" in request.form and request.form["welcome_second"].isnumeric() and \
            0 < int(request.form["welcome_second"]) < 60:
            welcome_grace_period_second.set(c, auth["guild"], request.form["welcome_second"])

        if request.form["goodbye_channel"] == "unset":
            goodbye_channel.set(c, auth["guild"], "")
        elif validate_text_channel_id(request.form["goodbye_channel"]):
            goodbye_channel.set(c, auth["guild"], request.form["goodbye_channel"])
                
        if "goodbye_title" in request.form and 1 < len(request.form["goodbye_title"]) < 100:
            goodbye_message_title.set(c, auth["guild"], request.form["goodbye_title"])

        if "goodbye_msg" in request.form and 1 < len(request.form["goodbye_msg"]) < 1000:
            goodbye_message_message.set(c, auth["guild"], request.form["goodbye_msg"])
            
        if "goodbye_type" in request.form and request.form["goodbye_type"] in ["text", "embed"]:
            goodbye_message_type.set(c, auth["guild"], request.form["goodbye_type"])


@welcome_goodbye_bp.route("/settings/welcome_goodbye", methods=["GET", "POST"])
def welcome_goodbye_index():
    authorization = authorize("/settings/welcome_goodbye")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        handle_save(auth)

    with engine.begin() as c:
        welcome_chan = welcome_channel.get(c, auth["guild"])
        welcome_title = welcome_message_title.get(c, auth["guild"])
        welcome_msg = welcome_message_message.get(c, auth["guild"])
        welcome_type = welcome_message_type.get(c, auth["guild"])
        welcome_first = welcome_grace_period_first.get(c, auth["guild"])
        welcome_second = welcome_grace_period_second.get(c, auth["guild"])

        goodbye_chan = goodbye_channel.get(c, auth["guild"])
        goodbye_title = goodbye_message_title.get(c, auth["guild"])
        goodbye_msg = goodbye_message_message.get(c, auth["guild"])
        goodbye_type = goodbye_message_type.get(c, auth["guild"])

        channels = [{
            "id": i[0],
            "name": i[1]
        } for i in c.execute(
            select(synced_channels.c.cid, synced_channels.c.cname)
            .where((synced_channels.c.gid == auth["guild"]) & (synced_channels.c.ctype == "text"))
        )]

    return render_template("welcome_goodbye.html",
                            welcome_channel=welcome_chan, welcome_title=welcome_title, welcome_msg=welcome_msg, welcome_type=welcome_type,
                           welcome_first=welcome_first, welcome_second=welcome_second,
                           goodbye_channel=goodbye_chan, goodbye_title=goodbye_title, goodbye_msg=goodbye_msg, goodbye_type=goodbye_type,
                           channels=channels)
