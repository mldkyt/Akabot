from flask import Blueprint, redirect, render_template, request, session
from sqlalchemy import delete, insert, select, update

from database import engine, meow_back_settings, synced_channels
from utils.meow_back import awawa, barking, colon_3, meowing, owo, wafing
from web.webutils.discord_sync import validate_text_channel_id
from web.webutils.quick_response import quick_response
from web.webutils.tokens import authorize, get_token_data

meow_back_bp = Blueprint("meow_back", __name__, template_folder="templates")


def handle_post(auth):
    with engine.begin() as c:
        if request.form.get("meow"):
            meowing.set(c, auth["guild"], "true")
        else:
            meowing.set(c, auth["guild"], "false")

        if request.form.get("waf"):
            wafing.set(c, auth["guild"], "true")
        else:
            wafing.set(c, auth["guild"], "false")

        if request.form.get("bark"):
            barking.set(c, auth["guild"], "true")
        else:
            barking.set(c, auth["guild"], "false")

        if request.form.get("colon_3"):
            colon_3.set(c, auth["guild"], "true")
        else:
            colon_3.set(c, auth["guild"], "false")

        if request.form.get("owo"):
            owo.set(c, auth["guild"], "true")
        else:
            owo.set(c, auth["guild"], "false")

        if request.form.get("awawa"):
            awawa.set(c, auth["guild"], "true")
        else:
            awawa.set(c, auth["guild"], "false")


@meow_back_bp.route("/settings/meow_back", methods=["GET", "POST"])
def meow_back_index():
    authorization = authorize("/settings/meow_back")
    if authorization is not None:
        return authorization

    meow_back_channels = []
    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        handle_post(auth)
        return redirect("/settings/meow_back?tab=general", 303)

    active_tab = request.args.get("tab", "channels")
    if active_tab not in {"general", "channels"}:
        active_tab = "channels"

    with engine.begin() as c:
        meow = meowing.get(c, auth["guild"]) == "true"
        waf = wafing.get(c, auth["guild"]) == "true"
        bark = barking.get(c, auth["guild"]) == "true"
        colon_31 = colon_3.get(c, auth["guild"]) == "true"
        owo1 = owo.get(c, auth["guild"]) == "true"
        awa = awawa.get(c, auth["guild"]) == "true"

        fetched_channels = c.execute(
            select(
                meow_back_settings.c.cid,
                meow_back_settings.c.meow,
                meow_back_settings.c.waf,
                meow_back_settings.c.bark,
                meow_back_settings.c.colon_3,
                meow_back_settings.c.owo,
                meow_back_settings.c.awawa,
            )
            .where(meow_back_settings.c.gid == auth["guild"])
        ).fetchall()

        for fetched_channel in fetched_channels:
            channel_name = c.execute(
                select(synced_channels.c.cname).where(
                    synced_channels.c.cid == fetched_channel[0]
                )
            ).fetchone()
            if not channel_name:
                continue

            meow_back_channels.append(
                {
                    "id": fetched_channel[0],
                    "name": channel_name[0],
                    "meow": fetched_channel[1] == 1,
                    "waf": fetched_channel[2] == 1,
                    "bark": fetched_channel[3] == 1,
                    "colon_3": fetched_channel[4] == 1,
                    "owo": fetched_channel[5] == 1,
                    "awawa": fetched_channel[6] == 1,
                }
            )

        text_channels = [
            {"id": i[0], "name": i[1]}
            for i in c.execute(
                select(synced_channels.c.cid, synced_channels.c.cname).where(
                    (synced_channels.c.ctype == "text")
                    & (synced_channels.c.gid == auth["guild"])
                )
            ).fetchall()
        ]

    return render_template(
        "meow_back.html",
        meow=meow,
        waf=waf,
        bark=bark,
        colon_3=colon_31,
        owo=owo1,
        awawa=awa,
        meow_back_channels=meow_back_channels,
        text_channels=text_channels,
        active_tab=active_tab,
    )


@meow_back_bp.route("/settings/meow_back/channel", methods=["POST"])
def meow_back_channel():
    authorization = authorize("/settings/meow_back")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if "channel" not in request.form or not validate_text_channel_id(
        request.form["channel"]
    ):
        return redirect("/settings/meow_back?tab=channels", 303)

    if request.form.get("action") == "delete":
        with engine.begin() as c:
            c.execute(
                delete(meow_back_settings).where(
                    (meow_back_settings.c.cid == request.form["channel"])
                    & (meow_back_settings.c.gid == auth["guild"])
                )
            )
        return redirect("/settings/meow_back?tab=channels", 303)

    with engine.begin() as c:
        meow = 1 if request.form.get("meow") else 0
        waf = 1 if request.form.get("waf") else 0
        bark = 1 if request.form.get("bark") else 0
        colon_3 = 1 if request.form.get("colon_3") else 0
        owo = 1 if request.form.get("owo") else 0
        awawa = 1 if request.form.get("awawa") else 0

        existing = c.execute(
            select(meow_back_settings).where(
                meow_back_settings.c.cid == request.form["channel"]
            )
        ).fetchone()

        if existing is not None and existing.gid != auth["guild"]:
            return quick_response("That channel belongs to another guild", 400)

        if existing:
            if meow + waf + bark + colon_3 + owo + awawa == 0:
                c.execute(
                    delete(meow_back_settings).where(
                        (meow_back_settings.c.cid == request.form["channel"])
                        & (meow_back_settings.c.gid == auth["guild"])
                    )
                )
            else:
                c.execute(
                    update(meow_back_settings)
                    .values(
                        meow=meow,
                        waf=waf,
                        bark=bark,
                        colon_3=colon_3,
                        owo=owo,
                        awawa=awawa,
                    )
                    .where(
                        (meow_back_settings.c.cid == request.form["channel"])
                        & (meow_back_settings.c.gid == auth["guild"])
                    )
                )
        else:
            c.execute(
                insert(meow_back_settings).values(
                    cid=request.form["channel"],
                    gid=auth["guild"],
                    meow=meow,
                    waf=waf,
                    bark=bark,
                    colon_3=colon_3,
                    owo=owo,
                    awawa=awawa,
                )
            )

    return redirect("/settings/meow_back?tab=channels", 303)
