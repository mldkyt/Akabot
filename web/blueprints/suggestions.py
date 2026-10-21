from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import delete, insert, select, update

from database import engine, suggestion_channels, synced_channels
from utils.suggestions import get_bot_permissions, suggestion_threads
from web.webutils.tokens import authorize, get_token_data

suggestions_bp = Blueprint("suggestions", __name__, template_folder="templates")


def _channel_is_valid(c, guild, channel_id):
    return (
        c.execute(
            select(synced_channels.c.cid).where(
                (synced_channels.c.gid == guild)
                & (synced_channels.c.cid == channel_id)
                & (synced_channels.c.ctype == "text")
            )
        ).fetchone()
        is not None
    )


@suggestions_bp.route("/settings/suggestions", methods=["GET", "POST"])
def suggestions_index():
    authorization = authorize("/settings/suggestions")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        section = request.form.get("_section", "general")
        if section == "general":
            with engine.begin() as c:
                if request.form.get("threads"):
                    suggestion_threads.set(c, auth["guild"], "true")
                else:
                    suggestion_threads.set(c, auth["guild"], "false")
            return redirect("/settings/suggestions?tab=general", 303)

        action = request.form.get("action", "create")
        channel = request.form.get("channel", "")
        old_channel = request.form.get("id", "")

        with engine.begin() as c:
            if action == "delete":
                if old_channel:
                    c.execute(
                        delete(suggestion_channels).where(
                            (suggestion_channels.c.gid == auth["guild"])
                            & (suggestion_channels.c.cid == old_channel)
                        )
                    )
                    flash("Removed suggestion channel")
            elif not _channel_is_valid(c, auth["guild"], channel):
                flash("Unknown channel")
            else:
                conflict = c.execute(
                    select(suggestion_channels.c.cid).where(
                        (suggestion_channels.c.gid == auth["guild"])
                        & (suggestion_channels.c.cid == channel)
                    )
                ).fetchone()
                if conflict is not None and channel != old_channel:
                    flash("That channel is already a suggestion channel")
                elif action == "update" and old_channel:
                    c.execute(
                        update(suggestion_channels)
                        .where(
                            (suggestion_channels.c.gid == auth["guild"])
                            & (suggestion_channels.c.cid == old_channel)
                        )
                        .values(cid=channel)
                    )
                    flash("Saved suggestion channel")
                else:
                    c.execute(
                        insert(suggestion_channels).values(
                            gid=auth["guild"], cid=channel
                        )
                    )
                    flash("Added suggestion channel")

        return redirect(
            f"/settings/suggestions?tab={request.form.get('_tab', 'channels')}", 303
        )

    active_tab = request.args.get("tab", "channels")
    if active_tab not in {"general", "channels"}:
        active_tab = "channels"

    with engine.begin() as c:
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
        res_suggestion_channels = []
        for suggestion_channel in suggestion_channel_rows:
            channel_name = c.execute(
                select(synced_channels.c.cname).where(
                    (synced_channels.c.cid == suggestion_channel[0])
                    & (synced_channels.c.gid == auth["guild"])
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
        all_channels_ok=all_channels_ok,
        active_tab=active_tab,
    )
