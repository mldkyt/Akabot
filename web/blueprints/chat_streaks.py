from flask import Blueprint, flash, redirect, render_template, request, session

from database import engine
from utils.chat_streaks import (
    server_streak_minimum,
    server_streak_minimum_enabled,
    server_streak_same_member_check,
)
from web.webutils.tokens import authorize, get_token_data

chat_streaks_bp = Blueprint("chat_streaks", __name__, template_folder="templates")


def save_settings(auth):
    if request.method != "POST":
        return

    # Minimum message requirement
    if "streakminimumenable" in request.form:
        with engine.begin() as c:
            server_streak_minimum_enabled.set(c, auth["guild"], "true")
    else:
        with engine.begin() as c:
            server_streak_minimum_enabled.set(c, auth["guild"], "false")

    if "streakminimum" in request.form:
        if request.form["streakminimum"].isnumeric() and int(
            request.form["streakminimum"]
        ) > 0:
            with engine.begin() as c:
                server_streak_minimum.set(
                    c, auth["guild"], request.form["streakminimum"]
                )
        else:
            flash(
                f"Invalid value {request.form['streakminimum']} for minimum chat streak messages. Must be a positive number."
            )

    if "streaksamemember" in request.form:
        with engine.begin() as c:
            server_streak_same_member_check.set(c, auth["guild"], "true")
    else:
        with engine.begin() as c:
            server_streak_same_member_check.set(c, auth["guild"], "false")


@chat_streaks_bp.route("/settings/chat_streaks", methods=["GET", "POST"])
def chat_streaks_index():
    authorization = authorize("/settings/chat_streaks")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        save_settings(auth)
        return redirect("/settings/chat_streaks", 303)

    with engine.begin() as c:
        minimum_enabled = server_streak_minimum_enabled.get(c, auth["guild"])
        minimum_messages = server_streak_minimum.get(c, auth["guild"])
        same_member_check = server_streak_same_member_check.get(c, auth["guild"])

    return render_template(
        "chat_streaks.html",
        minimum_enabled=minimum_enabled,
        minimum_messages=minimum_messages,
        same_member_check=same_member_check,
    )
