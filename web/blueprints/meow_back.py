from flask import Blueprint, session, render_template, request

from database import engine
from utils.meow_back import meowing, wafing, barking, colon_3, owo, awawa
from web.webutils.tokens import authorize, get_token_data

meow_back_bp = Blueprint("meow_back", __name__)

def handle_post(auth):
    with engine.begin() as c:
        if request.form.get("meow"):
            meowing.direct_set(c, auth["guild"], "true")
        else:
            meowing.direct_set(c, auth["guild"], "false")

        if request.form.get("waf"):
            wafing.direct_set(c, auth["guild"], "true")
        else:
            wafing.direct_set(c, auth["guild"], "false")

        if request.form.get("bark"):
            barking.direct_set(c, auth["guild"], "true")
        else:
            barking.direct_set(c, auth["guild"], "false")

        if request.form.get("colon_3"):
            colon_3.direct_set(c, auth["guild"], "true")
        else:
            colon_3.direct_set(c, auth["guild"], "false")

        if request.form.get("owo"):
            owo.direct_set(c, auth["guild"], "true")
        else:
            owo.direct_set(c, auth["guild"], "false")

        if request.form.get("awawa"):
            awawa.direct_set(c, auth["guild"], "true")
        else:
            awawa.direct_set(c, auth["guild"], "false")

@meow_back_bp.route("/settings/meow_back", methods=["GET", "POST"])
def meow_back_index():
    authorization = authorize("/settings/meow_back")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        handle_post(auth)

    with engine.begin() as c:
        meow = meowing.get(c, auth["guild"]) == "true"
        waf = wafing.get(c, auth["guild"]) == "true"
        bark = barking.get(c, auth["guild"]) == "true"
        colon_31 = colon_3.get(c, auth["guild"]) == "true"
        owo1 = owo.get(c, auth["guild"]) == "true"
        awa = awawa.get(c, auth["guild"]) == "true"

    return render_template("meow_back.html",
                           meow=meow, waf=waf, bark=bark, colon_3=colon_31, owo=owo1, awawa=awa)
