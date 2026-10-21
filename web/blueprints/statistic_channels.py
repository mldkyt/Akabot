from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import delete, insert, select, update

from database import engine, statistic_channels, synced_channels
from web.webutils.tokens import authorize, get_token_data

statistic_channels_bp = Blueprint("statistic_channels", __name__, template_folder="templates")


def _validate(c, guild, channel, template, old_channel=None):
    if not channel:
        return "Choose a voice channel"
    if c.execute(
        select(synced_channels.c.cid).where(
            (synced_channels.c.gid == guild)
            & (synced_channels.c.cid == channel)
            & (synced_channels.c.ctype == "voice")
        )
    ).fetchone() is None:
        return "Invalid voice channel selected"
    if not 2 <= len(template) <= 50:
        return "Template too short or too long, keep it between 2 and 50 characters"
    if ";" in template:
        return "The template must not have semicolons"

    conflict = c.execute(
        select(statistic_channels.c.cid).where(
            (statistic_channels.c.gid == guild)
            & (statistic_channels.c.cid == channel)
        )
    ).fetchone()
    if conflict is not None and channel != old_channel:
        return "This channel already has a template assigned"
    return None


@statistic_channels_bp.route("/settings/statistic_channels", methods=["GET", "POST"])
def statistic_channels_index():
    authorization = authorize("/settings/statistic_channels")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        action = request.form.get("action", "create")
        channel = request.form.get("channel", "")
        template = request.form.get("template", "")
        old_channel = request.form.get("id", "")

        with engine.begin() as c:
            if action == "delete":
                if old_channel:
                    c.execute(
                        delete(statistic_channels).where(
                            (statistic_channels.c.gid == auth["guild"])
                            & (statistic_channels.c.cid == old_channel)
                        )
                    )
                    flash("Deleted statistic channel")
            else:
                error = _validate(
                    c,
                    auth["guild"],
                    channel,
                    template,
                    old_channel if action == "update" else None,
                )
                if error is not None:
                    flash(error)
                elif action == "update" and old_channel:
                    c.execute(
                        update(statistic_channels)
                        .where(
                            (statistic_channels.c.gid == auth["guild"])
                            & (statistic_channels.c.cid == old_channel)
                        )
                        .values(cid=channel, template=template)
                    )
                    flash("Saved statistic channel")
                else:
                    c.execute(
                        insert(statistic_channels).values(
                            gid=auth["guild"],
                            cid=channel,
                            template=template,
                        )
                    )
                    flash("Added statistic channel")

        return redirect(
            f"/settings/statistic_channels?tab={request.form.get('_tab', 'channels')}",
            303,
        )

    active_tab = request.args.get("tab", "channels")
    if active_tab not in {"general", "channels"}:
        active_tab = "channels"

    with engine.begin() as c:
        statistic_channels_rows = c.execute(
            select(statistic_channels.c.cid, statistic_channels.c.template)
            .where(statistic_channels.c.gid == auth["guild"])
            .order_by(statistic_channels.c.id)
        ).fetchall()
        statistic_channels_list = []
        for i in range(len(statistic_channels_rows)):
            args = statistic_channels_rows[i]
            channel_name = c.execute(
                select(synced_channels.c.cname).where(
                    (synced_channels.c.cid == args[0])
                    & (synced_channels.c.gid == auth["guild"])
                )
            ).fetchone()

            if channel_name is None:
                continue

            statistic_channels_list.append(
                {
                    "index": i,
                    "id": args[0],
                    "name": channel_name[0],
                    "template": args[1],
                }
            )

        channels = [
            {"id": i[0], "name": i[1]}
            for i in c.execute(
                select(synced_channels.c.cid, synced_channels.c.cname).where(
                    (synced_channels.c.gid == auth["guild"])
                    & (synced_channels.c.ctype == "voice")
                )
            ).fetchall()
        ]

    return render_template(
        "statistic_channels.html",
        statistic_channels=statistic_channels_list,
        channels=channels,
        active_tab=active_tab,
    )
