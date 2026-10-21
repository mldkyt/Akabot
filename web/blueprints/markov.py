from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import delete, insert, select, update

from database import engine, markov, synced_channels
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
            section = request.form.get("_section", "add")
            if section == "add":
                channel = request.form.get("channel")
                period = request.form.get("period")
                mode = request.form.get("mode")
                messages_num = request.form.get("messages_num")
                num_periods = request.form.get("num_periods", "")

                if (
                    channel
                    and period
                    and mode in ["periodic", "messages", "command"]
                    and messages_num
                    and messages_num.isnumeric()
                    and num_periods.isnumeric()
                    and int(messages_num) >= 1
                ):
                    existing = c.execute(
                        select(markov).where(markov.c.channel_id == channel)
                    ).fetchone()

                    if existing is not None and existing.guild_id != auth["guild"]:
                        flash("That channel belongs to another guild")
                    elif existing is None:
                        c.execute(
                            insert(markov).values(
                                channel_id=channel,
                                guild_id=auth["guild"],
                                period=period,
                                period_num=int(num_periods),
                                mode=mode,
                                messages_num=int(messages_num),
                            )
                        )
                        flash("Added markov channel")
                    else:
                        c.execute(
                            update(markov)
                            .values(
                                period=period,
                                period_num=int(num_periods),
                                mode=mode,
                                messages_num=int(messages_num),
                            )
                            .where(
                                (markov.c.channel_id == channel)
                                & (markov.c.guild_id == auth["guild"])
                            )
                        )
                        flash("Edited markov channel")
                else:
                    flash("Invalid markov settings")

                return redirect("/settings/markov?tab=add", 303)

            action = request.form.get("action", "update")
            channel = request.form.get("channel", "")
            if action == "update" and channel:
                mode = request.form.get("mode")
                messages_num = request.form.get("messages_num", "")
                num_periods = request.form.get("num_periods", "")
                if (
                    mode in ["periodic", "messages", "command"]
                    and messages_num.isnumeric()
                    and num_periods.isnumeric()
                    and int(messages_num) >= 1
                ):
                    c.execute(
                        update(markov)
                        .values(
                            period=request.form.get("period"),
                            period_num=int(num_periods),
                            mode=mode,
                            messages_num=int(messages_num),
                        )
                        .where(
                            (markov.c.channel_id == channel)
                            & (markov.c.guild_id == auth["guild"])
                        )
                    )
                    flash("Edited markov channel")
                else:
                    flash("Invalid markov settings")
            elif action == "delete" and channel:
                c.execute(
                    delete(markov).where(
                        (markov.c.channel_id == channel)
                        & (markov.c.guild_id == auth["guild"])
                    )
                )
                flash("Disabled markov channel")

            return redirect("/settings/markov?tab=channels", 303)

        active_tab = request.args.get("tab", "channels")
        if active_tab not in {"channels", "add"}:
            active_tab = "channels"

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

    return render_template(
        "markov.html",
        text_channels=text_channels,
        enabled_channels=enabled_channels,
        active_tab=active_tab,
    )
