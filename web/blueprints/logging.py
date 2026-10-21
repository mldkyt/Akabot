from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import delete, insert, select

from database import engine, logging_channels, synced_channels
from utils.logs import logging_channel, logging_settings
from web.webutils.discord_sync import validate_text_channel_id
from web.webutils.tokens import authorize, get_token_data

logging_bp = Blueprint("logging", __name__, template_folder="templates")


def handle_saving_settings(auth):
    with engine.begin() as c:
        if "channel_id" in request.form:
            if not validate_text_channel_id(request.form["channel_id"]):
                return

            c.execute(
                delete(logging_channels).where(
                    (logging_channels.c.cid == request.form["channel_id"])
                    & (logging_channels.c.gid == auth["guild"])
                )
            )

            for i in logging_settings:
                if request.form.get(i[0]) == "on":
                    c.execute(
                        insert(logging_channels).values(
                            gid=auth["guild"], cid=request.form["channel_id"], type=i[0]
                        )
                    )

        if "delete" in request.form:
            c.execute(
                delete(logging_channels).where(
                    (logging_channels.c.cid == request.form["delete"])
                    & (logging_channels.c.gid == auth["guild"])
                )
            )


@logging_bp.route("/settings/logging", methods=["GET", "POST"])
def logging_index():
    authorization = authorize("/settings/logging")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        handle_saving_settings(auth)
        return redirect(f"/settings/logging?tab={request.form.get('_tab', 'channels')}", 303)

    active_tab = request.args.get("tab", "channels")
    if active_tab not in {"channels", "add"}:
        active_tab = "channels"

    settings = []
    with engine.begin() as c:
        logging_channel_id = logging_channel.get(c, auth["guild"])

        channels = [
            {"id": i[0], "name": i[1]}
            for i in c.execute(
                select(synced_channels.c.cid, synced_channels.c.cname).where(
                    (synced_channels.c.gid == auth["guild"])
                    & (synced_channels.c.ctype == "text")
                )
            ).fetchall()
        ]

        logging_channels_data = []

        for en_ch in c.execute(
            select(logging_channels.c.cid)
            .group_by(logging_channels.c.cid)
            .where(logging_channels.c.gid == auth["guild"])
        ):
            en_types = [
                i[0]
                for i in c.execute(
                    select(logging_channels.c.type).where(
                        logging_channels.c.cid == en_ch[0]
                    )
                ).fetchall()
            ]
            ch_name = [i for i in channels if i["id"] == en_ch[0]]
            ch_name = ch_name[0]["name"] if len(ch_name) > 0 else "Unknown"

            logging_channels_data.append(
                {"id": en_ch[0], "name": ch_name, "enabled": en_types}
            )

        for setting in logging_settings:
            settings.append(
                {
                    "key": setting[0],
                    "name": setting[1],
                }
            )

    return render_template(
        "logging.html",
        logging_channel=logging_channel_id,
        channels=channels,
        logging_channels=logging_channels_data,
        settings=settings,
        active_tab=active_tab,
    )
