from flask import Blueprint, flash, redirect, render_template, request, session
from sqlalchemy import select

from database import engine, synced_channels
from utils.bot_channel import setting_admin_bot_channel, setting_bot_channel
from utils.chat_streaks import server_message_delay, server_response_setting, server_response_name_setting
from utils.timezones import (
    get_timezone,
    invalidate_timezone_cache,
    is_valid_timezone,
    setting_timezone,
)
from web.webutils.discord_sync import validate_text_channel_id
from web.webutils.tokens import authorize, get_token_data

settings_index_bp = Blueprint("settings_index", __name__, template_folder="templates")


def get_timezone_groups() -> list[tuple[str, list[str]]]:
    """IANA timezones grouped by region, for the settings dropdown."""
    from zoneinfo import available_timezones

    regions: dict[str, list[str]] = {}
    for tz in sorted(available_timezones()):
        if "/" not in tz:
            continue
        region, _ = tz.split("/", 1)
        regions.setdefault(region, []).append(tz)

    return sorted(regions.items())


def save_settings(auth):
    if request.method != "POST":
        return

    # Bot channel
    if "botchannel" in request.form:
        if request.form["botchannel"] == "unset":
            with engine.begin() as c:
                setting_bot_channel.set(c, auth["guild"], "")
        elif validate_text_channel_id(request.form["botchannel"]):
            with engine.begin() as c:
                setting_bot_channel.set(c, auth["guild"], request.form["botchannel"])
        else:
            flash("Bot channel property found but the value was invalid.")

    # Admin bot channel
    if "adminbotchannel" in request.form:
        if request.form["adminbotchannel"] == "unset":
            with engine.begin() as c:
                setting_admin_bot_channel.set(c, auth["guild"], "")
        elif validate_text_channel_id(request.form["adminbotchannel"]):
            with engine.begin() as c:
                setting_admin_bot_channel.set(
                    c, auth["guild"], request.form["adminbotchannel"]
                )
        else:
            flash("Admin bot channel property found but the value was invalid.")

    # Response setting
    if "response" in request.form:
        if request.form["response"] in ["on", "bot", "bot_noping", "off"]:
            with engine.begin() as c:
                server_response_setting.set(c, auth["guild"], request.form["response"])
        else:
            flash(f"Invalid value {request.form['response']} for bot response setting")

    # Response name setting
    if "response_name" in request.form:
        if request.form["response_name"] in ["global_name", "display_name"]:
            with engine.begin() as c:
                server_response_name_setting.set(c, auth["guild"], request.form["response_name"])
        else:
            flash(f"Invalid value {request.form['response_name']} for bot response name setting")

    if "responsedelete" in request.form:
        if (
            request.form["responsedelete"].isnumeric()
            and 2 < int(request.form["responsedelete"]) < 60
        ):
            with engine.begin() as c:
                server_message_delay.set(
                    c, auth["guild"], request.form["responsedelete"]
                )
        else:
            flash(
                f"Invalid value {request.form['responsedelete']} for response delete delay. Must be between 2 seconds and 60 seconds."
            )

    # Timezone
    if "timezone" in request.form:
        if is_valid_timezone(request.form["timezone"]):
            with engine.begin() as c:
                setting_timezone.set(c, auth["guild"], request.form["timezone"])
            invalidate_timezone_cache(auth["guild"])
        else:
            flash(f"Invalid timezone {request.form['timezone']}")


@settings_index_bp.route("/settings", methods=["GET", "POST"])
def settings_index():
    authorization = authorize("/settings")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    if request.method == "POST":
        save_settings(auth)
        return redirect(f"/settings?tab={request.form.get('_tab', 'general')}", 303)

    active_tab = request.args.get("tab", "general")
    if active_tab not in {"general", "responses"}:
        active_tab = "general"

    with engine.begin() as c:
        bot_chan = setting_bot_channel.get(c, auth["guild"])
        admin_bot_chan = setting_admin_bot_channel.get(c, auth["guild"])
        text_channels = [
            {"id": i[0], "name": i[1]}
            for i in c.execute(
                select(synced_channels.c.cid, synced_channels.c.cname).where(
                    (synced_channels.c.gid == str(auth["guild"]))
                    & (synced_channels.c.ctype == "text")
                )
            )
        ]

        response = server_response_setting.get(c, auth["guild"])
        response_name = server_response_name_setting.get(c, auth["guild"])
        response_delete_delay = server_message_delay.get(c, auth["guild"])
        timezone = get_timezone(auth["guild"], c)

    return render_template(
        "index.html",
        current_bot_channel=bot_chan,
        current_admin_bot_channel=admin_bot_chan,
        text_channels=text_channels,
        response=response,
        response_name=response_name,
        response_delete_delay=response_delete_delay,
        timezone=timezone,
        timezone_groups=get_timezone_groups(),
        active_tab=active_tab,
    )
