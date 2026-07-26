from flask import Blueprint, render_template, request, session

from database import engine
from utils.message_counting import (
    setting_count_deletes,
    setting_enable_indexer,
    setting_enable_leaderboard,
)
from web.webutils.tokens import authorize, get_token_data

message_counting_bp = Blueprint(
    "message_counting", __name__, template_folder="templates"
)


@message_counting_bp.route("/settings/message_counting", methods=["GET", "POST"])
def message_counting_index():
    authorization = authorize("/settings/message_counting")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        if request.method == "POST":
            if request.form.get("enable_leaderboard"):
                setting_enable_leaderboard.set(c, auth["guild"], "true")
            else:
                setting_enable_leaderboard.set(c, auth["guild"], "false")

            if request.form.get("enable_indexer"):
                setting_enable_indexer.set(c, auth["guild"], "true")
            else:
                setting_enable_indexer.set(c, auth["guild"], "false")

            if request.form.get("count_deletes"):
                setting_count_deletes.set(c, auth["guild"], "true")
            else:
                setting_count_deletes.set(c, auth["guild"], "false")

        enable_leaderboard = setting_enable_leaderboard.get(c, auth["guild"]) == "true"
        enable_indexer = setting_enable_indexer.get(c, auth["guild"]) == "true"
        count_deletes = setting_count_deletes.get(c, auth["guild"]) == "true"

    return render_template(
        "message_counting.html",
        enable_leaderboard=enable_leaderboard,
        enable_indexer=enable_indexer,
        count_deletes=count_deletes,
    )
