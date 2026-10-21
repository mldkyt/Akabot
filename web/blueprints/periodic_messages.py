from datetime import timedelta

from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import delete, insert, select, update

from database import engine, periodic_messages, synced_channels
from utils.timezones import get_now
from web.webutils.tokens import authorize, get_token_data

periodic_messages_bp = Blueprint(
    "periodic_messages", __name__, template_folder="templates"
)


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


@periodic_messages_bp.route("/settings/periodic_messages", methods=["GET", "POST"])
def periodic_messages_index():
    authorization = authorize("/settings/periodic_messages")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        section = request.form.get("_section", "manage")
        action = request.form.get("action", "create")
        channel = request.form.get("channel", "")
        period = request.form.get("period", "")
        period_num = request.form.get("period_num", "")
        content = request.form.get("content", "")

        with engine.begin() as c:
            if action == "delete":
                channel = request.form.get("id", "")
                if channel:
                    c.execute(
                        delete(periodic_messages).where(
                            (periodic_messages.c.channel_id == channel)
                            & (periodic_messages.c.guild_id == auth["guild"])
                        )
                    )
                    flash("Deleted periodic message")
            elif (
                channel
                and period in {"daily", "weekly", "monthly", "yearly"}
                and period_num.isnumeric()
                and int(period_num) >= 1
                and content
            ):
                if not _channel_is_valid(c, auth["guild"], channel):
                    flash("Unknown channel")
                elif action == "update":
                    old_channel = request.form.get("id", "")
                    conflict = c.execute(
                        select(periodic_messages.c.id).where(
                            (periodic_messages.c.channel_id == channel)
                            & (periodic_messages.c.guild_id == auth["guild"])
                            & (periodic_messages.c.channel_id != old_channel)
                        )
                    ).fetchone()
                    if conflict is not None:
                        flash("That channel already has a periodic message")
                    else:
                        now = get_now(auth["guild"], c)
                        c.execute(
                            update(periodic_messages)
                            .values(
                                channel_id=channel,
                                period=period,
                                period_num=int(period_num),
                                content=content,
                                next_send=now + timedelta(minutes=int(period_num)),
                            )
                            .where(
                                (periodic_messages.c.channel_id == old_channel)
                                & (periodic_messages.c.guild_id == auth["guild"])
                            )
                        )
                        flash("Saved periodic message")
                else:
                    existing = c.execute(
                        select(periodic_messages.c.id).where(
                            (periodic_messages.c.channel_id == channel)
                            & (periodic_messages.c.guild_id == auth["guild"])
                        )
                    ).fetchone()
                    if existing is not None:
                        flash("That channel already has a periodic message")
                    else:
                        now = get_now(auth["guild"], c)
                        c.execute(
                            insert(periodic_messages).values(
                                channel_id=channel,
                                guild_id=auth["guild"],
                                period=period,
                                period_num=int(period_num),
                                content=content,
                                next_send=now + timedelta(minutes=int(period_num)),
                            )
                        )
                        flash("Added periodic message")
            else:
                flash("Please fill in all fields")

        return redirect(
            f"/settings/periodic_messages?tab={request.form.get('_tab', 'manage')}",
            303,
        )

    active_tab = request.args.get("tab", "manage")
    if active_tab not in {"manage", "create"}:
        active_tab = "manage"

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

        periodic_messages_data = []

        for i in c.execute(
            select(
                periodic_messages.c.id,
                periodic_messages.c.channel_id,
                periodic_messages.c.period,
                periodic_messages.c.period_num,
                periodic_messages.c.content,
            ).where(periodic_messages.c.guild_id == auth["guild"])
        ).fetchall():
            channel_info = c.execute(
                select(synced_channels.c.cname).where(
                    (synced_channels.c.cid == i[1])
                    & (synced_channels.c.gid == auth["guild"])
                )
            ).fetchone()

            periodic_messages_data.append(
                {
                    "id": i[0],
                    "channel_id": i[1],
                    "period": i[2],
                    "period_num": i[3],
                    "content": i[4],
                    "name": channel_info[0] if channel_info else "Unknown Channel",
                }
            )

    return render_template(
        "periodic_messages.html",
        text_channels=text_channels,
        periodic_messages=periodic_messages_data,
        active_tab=active_tab,
    )
