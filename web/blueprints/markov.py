from flask import Blueprint, render_template, request, session
from sqlalchemy import delete, insert, select, update

from database import engine, markov, synced_channels
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
            if request.form.get("channel") and request.form.get("period"):
                # Check if the channel already has settings
                row = c.execute(
                    select(markov).where(markov.c.channel_id == request.form["channel"])
                ).fetchone()

                if not row:
                    c.execute(
                        insert(markov).values(
                            channel_id=request.form["channel"],
                            guild_id=auth["guild"],
                            period=request.form["period"],
                            period_num=int(request.form["num_periods"]),
                        )
                    )
                else:
                    c.execute(
                        update(markov)
                        .values(
                            period=request.form["period"],
                            period_num=int(request.form["num_periods"]),
                        )
                        .where(markov.c.channel_id == request.form["channel"])
                    )
            elif request.form.get("delete"):
                c.execute(
                    delete(markov).where(markov.c.channel_id == request.form["delete"])
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
            {"id": i[0], "name": i[1], "period": i[2], "period_num": i[3]}
            for i in c.execute(
                select(
                    synced_channels.c.cid,
                    synced_channels.c.cname,
                    markov.c.period,
                    markov.c.period_num,
                )
                .join(
                    markov,
                    synced_channels.c.cid == markov.c.channel_id,
                )
                .where(markov.c.guild_id == auth["guild"])
            ).fetchall()
        ]

    return render_template(
        "markov.html",
        text_channels=text_channels,
        enabled_channels=enabled_channels,
    )
