from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, session
from sqlalchemy import delete, insert, select, update

from database import engine, periodic_messages, synced_channels
from web.webutils.tokens import authorize, get_token_data

periodic_messages_bp = Blueprint(
    "periodic_messages", __name__, template_folder="templates"
)


@periodic_messages_bp.route("/settings/periodic_messages", methods=["GET", "POST"])
def periodic_messages_index():
    authorization = authorize("/settings/periodic_messages")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    with engine.begin() as c:
        if request.method == "POST":
            if (
                request.form.get("channel")
                and request.form.get("period")
                and request.form.get("period_num")
                and request.form.get("content")
            ):
                existing = c.execute(
                    select(periodic_messages).where(
                        periodic_messages.c.channel_id == request.form["channel"]
                    )
                ).fetchone()

                if existing:
                    c.execute(
                        update(periodic_messages)
                        .values(
                            period=request.form["period"],
                            period_num=int(request.form["period_num"]),
                            content=request.form["content"],
                            next_send=datetime.now()
                            + timedelta(minutes=int(request.form["period_num"])),
                        )
                        .where(
                            periodic_messages.c.channel_id == request.form["channel"]
                        )
                    )
                else:
                    c.execute(
                        insert(periodic_messages).values(
                            channel_id=request.form["channel"],
                            guild_id=auth["guild"],
                            period=request.form["period"],
                            period_num=int(request.form["period_num"]),
                            content=request.form["content"],
                            next_send=datetime.now()
                            + timedelta(minutes=int(request.form["period_num"])),
                        )
                    )

            elif request.form.get("delete"):
                c.execute(
                    delete(periodic_messages).where(
                        periodic_messages.c.channel_id == request.form["delete"]
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
                select(synced_channels.c.cname).where(synced_channels.c.cid == i[1])
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
    )
