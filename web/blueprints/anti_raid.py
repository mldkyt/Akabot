from flask import Blueprint, render_template, request, session

from database import engine
from utils.anti_raid import setting_minimum_age, setting_no_avatar
from web.webutils.tokens import authorize, get_token_data

anti_raid_bp = Blueprint("anti_raid", __name__, template_folder="templates")


@anti_raid_bp.route("/settings/anti_raid", methods=["GET", "POST"])
def anti_raid_index():
    authorization = authorize("/settings/anti_raid")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        if request.method == "POST":
            if request.form.get("kick_no_pfp"):
                setting_no_avatar.set(c, auth["guild"], "true")
            else:
                setting_no_avatar.set(c, auth["guild"], "false")

            if (
                request.form.get("kick_min_age")
                and request.form["kick_min_age"].isnumeric()
                and 0 <= int(request.form["kick_min_age"]) < 31
            ):
                setting_minimum_age.set(c, auth["guild"], request.form["kick_min_age"])

        kick_no_pfp = setting_no_avatar.get(c, auth["guild"]) == "true"
        kick_min_age = setting_minimum_age.get(c, auth["guild"])

    return render_template(
        "anti_raid.html", kick_no_pfp=kick_no_pfp, kick_min_age=kick_min_age
    )
