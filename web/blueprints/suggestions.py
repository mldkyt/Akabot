from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import delete, insert, select

from database import engine, suggestion_channels, synced_channels
from utils.suggestions import get_bot_permissions, suggestion_threads
from utils.premium import get_limit, get_premium_context
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

        suggestion_channel_rows = c.execute(
            select(suggestion_channels.c.cid)
            .where(suggestion_channels.c.gid == auth["guild"])
            .order_by(suggestion_channels.c.id)
        ).fetchall()
        bot_permissions = get_bot_permissions(c, auth["guild"])
        for suggestion_channel in suggestion_channel_rows:
            channel_name = c.execute(
                select(synced_channels.c.cname).where(
                    synced_channels.c.cid == suggestion_channel[0]
                )
            ).fetchone()

            res_suggestion_channels.append(
                {
                    "name": channel_name[0] if channel_name is not None else "unknown",
                    "id": suggestion_channel[0],
                    "bot_ok": bot_permissions.get(suggestion_channel[0], True),
                }
            )

        all_channels_ok = all(i["bot_ok"] for i in res_suggestion_channels)

        suggestion_threads_val = suggestion_threads.get(c, auth["guild"]) == "true"

    return render_template(
        "suggestions.html",
        text_channels=text_channels,
        suggestion_channels=res_suggestion_channels,
        suggestion_threads=suggestion_threads_val,
        premium=get_premium_context(c, auth["guild"]),
        all_channels_ok=all_channels_ok,
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

            existing = c.execute(
                select(suggestion_channels.c.cid).where(
                    (suggestion_channels.c.gid == auth["guild"])
                    & (suggestion_channels.c.cid == request.form["channel"])
                )
            ).fetchone()
            if existing is not None:
                return redirect("/settings/suggestions", 303)

            limit = get_limit(c, auth["guild"], 1)
            current_count = len(
                c.execute(
                    select(suggestion_channels.c.cid).where(
                        suggestion_channels.c.gid == auth["guild"]
                    )
                ).fetchall()
            )
            if limit is not None and current_count >= limit:
                flash("Free plan is limited to 1 suggestion channel")
                return redirect("/settings/suggestions", 303)

            c.execute(
                insert(suggestion_channels).values(
                    gid=auth["guild"], cid=request.form["channel"]
                )
            )

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

            c.execute(
                delete(suggestion_channels).where(
                    (suggestion_channels.c.gid == auth["guild"])
                    & (suggestion_channels.c.cid == request.form["channel"])
                )
            )

    return redirect("/settings/suggestions", 303)
