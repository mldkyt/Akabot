from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import delete, insert, select, update

from database import engine, synced_channels, temporary_vc_creator_channels
from web.webutils.tokens import authorize, get_token_data

temporary_vcs_bp = Blueprint("temporary_vcs", __name__, template_folder="templates")


@temporary_vcs_bp.route("/settings/temporary_vcs", methods=["GET", "POST"])
def temporary_vcs_index():
    authorization = authorize("/settings/temporary_vcs")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        section = request.form.get("_section", "channels")
        action = request.form.get("action", "create")
        channel = request.form.get("channel", "")
        old_channel = request.form.get("id", "")

        if section == "channels":
            with engine.begin() as c:
                valid = c.execute(
                    select(synced_channels.c.cid).where(
                        (synced_channels.c.gid == auth["guild"])
                        & (synced_channels.c.cid == channel)
                        & (synced_channels.c.ctype == "voice")
                    )
                ).fetchone()

                if action == "delete":
                    if old_channel:
                        c.execute(
                            delete(temporary_vc_creator_channels).where(
                                (temporary_vc_creator_channels.c.gid == auth["guild"])
                                & (temporary_vc_creator_channels.c.cid == old_channel)
                            )
                        )
                        flash("Deleted temporary VC creator channel")
                elif valid is None:
                    flash("Invalid voice channel selected")
                else:
                    existing = c.execute(
                        select(temporary_vc_creator_channels.c.cid).where(
                            (temporary_vc_creator_channels.c.gid == auth["guild"])
                            & (temporary_vc_creator_channels.c.cid == channel)
                        )
                    ).fetchone()
                    if existing is not None and channel != old_channel:
                        flash("Already present")
                    elif action == "update" and old_channel:
                        c.execute(
                            update(temporary_vc_creator_channels)
                            .where(
                                (temporary_vc_creator_channels.c.gid == auth["guild"])
                                & (temporary_vc_creator_channels.c.cid == old_channel)
                            )
                            .values(cid=channel)
                        )
                        flash("Saved temporary VC creator channel")
                    else:
                        c.execute(
                            insert(temporary_vc_creator_channels).values(
                                gid=auth["guild"], cid=channel
                            )
                        )
                        flash("Added temporary VC creator channel")

        return redirect(
            f"/settings/temporary_vcs?tab={request.form.get('_tab', 'channels')}", 303
        )

    active_tab = request.args.get("tab", "general")
    if active_tab not in {"general", "channels"}:
        active_tab = "general"

    with engine.begin() as c:
        temporary_vcs_ids = [
            i[0]
            for i in c.execute(
                select(temporary_vc_creator_channels.c.cid)
                .where(temporary_vc_creator_channels.c.gid == auth["guild"])
                .order_by(temporary_vc_creator_channels.c.id)
            ).fetchall()
        ]
        temporary_vcs = []

        for i in range(len(temporary_vcs_ids)):
            name = c.execute(
                select(synced_channels.c.cname).where(
                    (synced_channels.c.cid == temporary_vcs_ids[i])
                    & (synced_channels.c.gid == auth["guild"])
                )
            ).fetchone()
            if name is None:
                continue

            temporary_vcs.append(
                {"index": i, "id": temporary_vcs_ids[i], "name": name[0]}
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
        "temporary_vcs.html",
        temporary_vcs=temporary_vcs,
        channels=channels,
        active_tab=active_tab,
    )
