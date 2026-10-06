from flask import Blueprint, render_template, request, session
from sqlalchemy import delete, insert, select, update

from database import engine, markov, synced_channels
from utils.premium import get_limit, get_premium_context
from web.webutils.quick_response import quick_response
from web.webutils.tokens import authorize, get_token_data

markov_bp = Blueprint("markov", __name__, template_folder="templates")


@markov_bp.route("/settings/markov", methods=["GET", "POST"])
def markov_index():
    authorization = authorize("/settings/markov")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        if request.method == "POST":
            if request.form.get("channel") and request.form.get("period") \
                    and request.form.get("mode") and request.form["mode"] in ["periodic", "messages", "command"] \
                    and request.form.get("messages_num") and request.form["messages_num"].isnumeric():

                if int(request.form["messages_num"]) <= 1:
                    return quick_response("The minimum messages number must be at least 1", 400)

                # Check if the channel already has settings
                row = c.execute(
                    select(markov).where(markov.c.channel_id == request.form["channel"])
                ).fetchone()

                if row is not None and row.guild_id != auth["guild"]:
                    return quick_response("That channel belongs to another guild", 400)

                if not row:
                    limit = get_limit(c, auth["guild"], 1)
                    markov_count = len(c.execute(
                        select(markov.c.channel_id).where(markov.c.guild_id == auth["guild"])
                    ).fetchall())
                    if limit is not None and markov_count >= limit:
                        return quick_response("Free plan is limited to 1 markov channel", 400)

                    c.execute(
                        insert(markov).values(
                            channel_id=request.form["channel"],
                            guild_id=auth["guild"],
                            period=request.form["period"],
                            period_num=int(request.form["num_periods"]),
                            mode=request.form["mode"],
                            messages_num=int(request.form["messages_num"]),
                        )
                    )
                else:
                    c.execute(
                        update(markov)
                        .values(
                            period=request.form["period"],
                            period_num=int(request.form["num_periods"]),
                            mode=request.form["mode"],
                            messages_num=int(request.form["messages_num"]),
                        )
                        .where(
                            (markov.c.channel_id == request.form["channel"])
                            & (markov.c.guild_id == auth["guild"])
                        )
                    )
            elif request.form.get("delete"):
                c.execute(
                    delete(markov).where(
                        (markov.c.channel_id == request.form["delete"])
                        & (markov.c.guild_id == auth["guild"])
                    )
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

        enabled_channels = [
            {"id": i[0], "name": i[1], "period": i[2], "period_num": i[3], "mode": i[4], "messages_num": i[5]}
            for i in c.execute(
                select(
                    synced_channels.c.cid,
                    synced_channels.c.cname,
                    markov.c.period,
                    markov.c.period_num,
                    markov.c.mode,
                    markov.c.messages_num,
                )
                .join(
                    markov,
                    synced_channels.c.cid == markov.c.channel_id,
                )
                .where(markov.c.guild_id == auth["guild"])
            ).fetchall()
        ]

        premium = get_premium_context(c, auth["guild"])

    return render_template(
        "markov.html",
        text_channels=text_channels,
        enabled_channels=enabled_channels,
        premium=premium,
    )
