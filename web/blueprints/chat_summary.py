from flask import Blueprint, session, render_template, request, flash, redirect
from sqlalchemy import delete, insert, select

from database import chat_summary_channels, engine, synced_channels
from utils.chat_summary import chat_summary_extra, chat_summary_history, chat_summary_rows, chat_summary_rows_extra, \
    chat_summary_unique
from web.webutils.discord_sync import validate_text_channel_id
from web.webutils.tokens import authorize, get_token_data

chat_summary_bp = Blueprint("chat_summary", __name__)

def handle_settings(auth):
    if "channel" in request.form:
        return

    with engine.begin() as c:
        if "row_count" in request.form and request.form["row_count"].isnumeric():
            if 10 >= int(request.form["row_count"]) >= 2:
                chat_summary_rows.set(c, auth["guild"], request.form["row_count"])
            else:
                flash("Row count must be between 2 and 10 rows")

        if request.form.get("unique_mode") == "on":
            chat_summary_unique.set(c, auth["guild"], "true")
        else:
            chat_summary_unique.set(c, auth["guild"], "false")

        if request.form.get("extra") == "on":
            chat_summary_extra.set(c, auth["guild"], "true")
        else:
            chat_summary_extra.set(c, auth["guild"], "false")

        if request.form.get("history") == "on":
            chat_summary_history.set(c, auth["guild"], "true")
        else:
            chat_summary_history.set(c, auth["guild"], "false")

        if "row_count_extra" in request.form and request.form["row_count_extra"].isnumeric():
            if 10 >= int(request.form["row_count_extra"]) >= 2:
                chat_summary_rows_extra.set(c, auth["guild"], request.form["row_count_extra"])
            else:
                flash("Extended row count must be between 2 and 10 rows")

def handle_adding_channels(auth):
    with engine.begin() as c:
        if "channel" in request.form and validate_text_channel_id(request.form["channel"]):
            existing = c.execute(
                select(chat_summary_channels.c.cid).where(
                    (chat_summary_channels.c.gid == str(auth["guild"]))
                    & (chat_summary_channels.c.cid == request.form["channel"])
                )
            ).fetchone()
            if existing is not None:
                flash("This channel was already added")
                return

            c.execute(
                insert(chat_summary_channels).values(
                    gid=str(auth["guild"]),
                    cid=request.form["channel"],
                    messages=0,
                    last_member="0",
                )
            )


def handle_delete(auth):
    with engine.begin() as c:
        c.execute(
            delete(chat_summary_channels).where(
                (chat_summary_channels.c.gid == str(auth["guild"]))
                & (chat_summary_channels.c.cid == request.args["delete"])
            )
        )


@chat_summary_bp.route("/settings/chat_summary", methods=["GET", "POST"])
def chat_summary_index():
    authorization = authorize("/settings/chat_summary")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        handle_settings(auth)
        handle_adding_channels(auth)

    if "delete" in request.args:
        handle_delete(auth)
        return redirect("/settings/chat_summary", 302)

    with engine.begin() as c:
        chans = [{
            "id": i[0],
            "name": i[1]
        } for i in c.execute(
            select(synced_channels.c.cid, synced_channels.c.cname)
            .where((synced_channels.c.gid == str(auth["guild"])) & (synced_channels.c.ctype == "text"))
        ).fetchall()]

        chat_summaries = []
        chs = [
            i[0]
            for i in c.execute(
                select(chat_summary_channels.c.cid)
                .where(chat_summary_channels.c.gid == str(auth["guild"]))
                .order_by(chat_summary_channels.c.cid)
            ).fetchall()
        ]
        for index in range(len(chs)):
            channel = chs[index]
            channel = c.execute(
                select(synced_channels.c.cname)
                .where((synced_channels.c.gid == str(auth["guild"])) & (synced_channels.c.cid == channel))
            ).fetchone()

            if channel is not None:
                chat_summaries.append({
                    "index": index,
                    "id": chs[index],
                    "channel": "#" + channel[0]
                })

        extra = chat_summary_extra.get(c, auth["guild"]) == "true"
        row_count = chat_summary_rows.get(c, auth["guild"])
        row_count_extra = chat_summary_rows_extra.get(c, auth["guild"])
        unique_mode = chat_summary_unique.get(c, auth["guild"]) == "true"
        history = chat_summary_history.get(c, auth["guild"]) == "true"

    return render_template("chat_summary.html", channels=chans,
                           chat_summaries=chat_summaries, extra=extra,
                           row_count=row_count, row_count_extra=row_count_extra,
                           unique_mode=unique_mode, history=history)
