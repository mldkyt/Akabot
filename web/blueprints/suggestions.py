from flask import Blueprint, redirect, render_template, request, session
from sqlalchemy import select

from database import engine, synced_channels
from utils.suggestions import suggestion_channels, suggestion_threads
from web.webutils.discord_sync import validate_text_channel_id
from web.webutils.tokens import authorize, get_token_data

suggestions_bp = Blueprint("suggestions", __name__, template_folder="templates")


@suggestions_bp.route("/settings/suggestions", methods=["GET", "POST"])
def suggestions_index():
    authorization = authorize("/settings/suggestions")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None
    res_suggestion_channels = []

    with engine.begin() as c:
        if request.method == "POST":
            if request.form.get("threads"):
                suggestion_threads.set(c, auth["guild"], "true")
            else:
                suggestion_threads.set(c, auth["guild"], "false")

        text_channels = [
            {"id": i[0], "name": i[1]}
            for i in c.execute(
                select(synced_channels.c.cid, synced_channels.c.cname).where(
                    (synced_channels.c.ctype == "text")
                    & (synced_channels.c.gid == auth["guild"])
                )
            ).fetchall()
        ]

        for suggestion_channel in suggestion_channels.get(c, auth["guild"]):
            channel_name = c.execute(
                select(synced_channels.c.cname).where(
                    synced_channels.c.cid == suggestion_channel
                )
            ).fetchone()

            res_suggestion_channels.append(
                {
                    "name": channel_name[0] if channel_name is not None else "unknown",
                    "id": suggestion_channel,
                }
            )

        suggestion_threads_val = suggestion_threads.get(c, auth["guild"]) == "true"

    return render_template(
        "suggestions.html",
        text_channels=text_channels,
        suggestion_channels=res_suggestion_channels,
        suggestion_threads=suggestion_threads_val,
    )


@suggestions_bp.route("/settings/suggestions/addchannel", methods=["POST"])
def suggestions_add_channel():
    authorization = authorize("/settings/suggestions")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        if request.method == "POST":
            if "channel" not in request.form:
                return redirect("/settings/suggestions", 303)

            if not validate_text_channel_id(request.form["channel"]):
                return redirect("/settings/suggestions", 303)

            if suggestion_channels.is_in_list(
                c, auth["guild"], request.form["channel"]
            ):
                return redirect("/settings/suggestions", 303)

            suggestion_channels.add_to_list(c, auth["guild"], request.form["channel"])

    return redirect("/settings/suggestions", 303)


@suggestions_bp.route("/settings/suggestions/deletechannel", methods=["POST"])
def suggestions_delete_channel():
    authorization = authorize("/settings/suggestions")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        if request.method == "POST":
            if "channel" not in request.form:
                return redirect("/settings/suggestions", 303)

            if not validate_text_channel_id(request.form["channel"]):
                return redirect("/settings/suggestions", 303)

            suggestion_channels.remove_from_list(
                c, auth["guild"], request.form["channel"]
            )

    return redirect("/settings/suggestions", 303)
