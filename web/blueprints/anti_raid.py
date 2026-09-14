from flask import Blueprint, flash, render_template, request, session

from database import engine
from utils.anti_raid import (
    message_intent_enabled,
    setting_caps_action,
    setting_caps_delete,
    setting_caps_dm,
    setting_caps_dm_message,
    setting_caps_enabled,
    setting_caps_min_length,
    setting_caps_percentage,
    setting_caps_reason,
    setting_caps_timeout,
    setting_duplicate_action,
    setting_duplicate_count,
    setting_duplicate_delete,
    setting_duplicate_dm,
    setting_duplicate_dm_message,
    setting_duplicate_enabled,
    setting_duplicate_reason,
    setting_duplicate_timeout,
    setting_duplicate_window,
    setting_emoji_action,
    setting_emoji_count,
    setting_emoji_delete,
    setting_emoji_dm,
    setting_emoji_dm_message,
    setting_emoji_enabled,
    setting_emoji_reason,
    setting_emoji_timeout,
    setting_emoji_window,
    setting_flood_action,
    setting_flood_count,
    setting_flood_delete,
    setting_flood_dm,
    setting_flood_dm_message,
    setting_flood_enabled,
    setting_flood_reason,
    setting_flood_timeout,
    setting_flood_window,
    setting_invite_action,
    setting_invite_count,
    setting_invite_delete,
    setting_invite_dm,
    setting_invite_dm_message,
    setting_invite_enabled,
    setting_invite_reason,
    setting_invite_timeout,
    setting_invite_window,
    setting_joinburst_action,
    setting_joinburst_count,
    setting_joinburst_dm,
    setting_joinburst_dm_message,
    setting_joinburst_enabled,
    setting_joinburst_reason,
    setting_joinburst_timeout,
    setting_joinburst_window,
    setting_mentions_action,
    setting_mentions_count,
    setting_mentions_delete,
    setting_mentions_dm,
    setting_mentions_dm_message,
    setting_mentions_enabled,
    setting_mentions_reason,
    setting_mentions_timeout,
    setting_minimum_age,
    setting_mrbeast_action,
    setting_mrbeast_delete,
    setting_mrbeast_dm,
    setting_mrbeast_dm_message,
    setting_mrbeast_reason,
    setting_mrbeast_scam,
    setting_mrbeast_timeout,
    setting_no_avatar,
    setting_sticker_action,
    setting_sticker_count,
    setting_sticker_delete,
    setting_sticker_dm,
    setting_sticker_dm_message,
    setting_sticker_enabled,
    setting_sticker_reason,
    setting_sticker_timeout,
    setting_sticker_window,
)
from utils.premium import get_premium_context
from web.webutils.tokens import authorize, get_token_data

anti_raid_bp = Blueprint("anti_raid", __name__, template_folder="templates")

VALID_ACTIONS = ("timeout", "kick", "ban", "log")
TEXT_MAX = 1000

BOUNDS = {
    "flood_count": (1, 100),
    "flood_window": (1, 600),
    "flood_timeout": (1, 2419200),
    "duplicate_count": (1, 100),
    "duplicate_window": (1, 600),
    "duplicate_timeout": (1, 2419200),
    "mentions_count": (1, 100),
    "mentions_timeout": (1, 2419200),
    "invite_count": (1, 100),
    "invite_window": (1, 3600),
    "invite_timeout": (1, 2419200),
    "caps_percentage": (1, 100),
    "caps_min_length": (1, 2000),
    "caps_timeout": (1, 2419200),
    "emoji_count": (1, 100),
    "emoji_window": (1, 600),
    "emoji_timeout": (1, 2419200),
    "sticker_count": (1, 100),
    "sticker_window": (1, 600),
    "sticker_timeout": (1, 2419200),
    "joinburst_count": (1, 100),
    "joinburst_window": (1, 3600),
    "joinburst_timeout": (1, 2419200),
    "mrbeast_timeout": (1, 2419200),
}

DETECTORS = [
    ("mrbeast", setting_mrbeast_timeout, setting_mrbeast_dm_message, setting_mrbeast_reason),
    ("flood", setting_flood_timeout, setting_flood_dm_message, setting_flood_reason),
    ("duplicate", setting_duplicate_timeout, setting_duplicate_dm_message, setting_duplicate_reason),
    ("mentions", setting_mentions_timeout, setting_mentions_dm_message, setting_mentions_reason),
    ("invite", setting_invite_timeout, setting_invite_dm_message, setting_invite_reason),
    ("caps", setting_caps_timeout, setting_caps_dm_message, setting_caps_reason),
    ("emoji", setting_emoji_timeout, setting_emoji_dm_message, setting_emoji_reason),
    ("sticker", setting_sticker_timeout, setting_sticker_dm_message, setting_sticker_reason),
    ("joinburst", setting_joinburst_timeout, setting_joinburst_dm_message, setting_joinburst_reason),
]

CONTENT_DETECTORS = frozenset({"duplicate", "mentions", "invite", "caps", "emoji"})


def _set_number(c, guild, setting, form_key):
    value = request.form.get(form_key)
    if value is None or not value.isnumeric():
        return
    low, high = BOUNDS[form_key]
    if low <= int(value) <= high:
        setting.set(c, guild, value)


def _set_checkbox(c, guild, setting, form_key):
    if request.form.get(form_key):
        setting.set(c, guild, "true")
    else:
        setting.set(c, guild, "false")


def _set_text(c, guild, setting, form_key):
    value = request.form.get(form_key)
    if value is not None and len(value) <= TEXT_MAX:
        setting.set(c, guild, value)


def _enabled_count(c, guild):
    count = 0
    for setting in (
        setting_mrbeast_scam,
        setting_flood_enabled,
        setting_duplicate_enabled,
        setting_mentions_enabled,
        setting_invite_enabled,
        setting_caps_enabled,
        setting_emoji_enabled,
        setting_sticker_enabled,
        setting_joinburst_enabled,
    ):
        if setting.get(c, guild) == "true":
            count += 1
    return count


def _set_enabled(c, guild, setting, form_key, free_tier, enabled_count):
    requested = bool(request.form.get(form_key))
    already = setting.get(c, guild) == "true"

    if requested:
        if free_tier and not already and enabled_count >= 3:
            flash("Free plan is limited to 3 enabled anti raid protections")
            return enabled_count
        setting.set(c, guild, "true")
        if not already:
            return enabled_count + 1
    else:
        setting.set(c, guild, "false")
        if already:
            return enabled_count - 1

    return enabled_count


@anti_raid_bp.route("/settings/anti_raid", methods=["GET", "POST"])
def anti_raid_index():
    authorization = authorize("/settings/anti_raid")
    if authorization is not None:
        return authorization

    auth = get_token_data(session["token"])
    assert auth is not None

    message_intent = message_intent_enabled()

    with engine.begin() as c:
        if request.method == "POST":
            free_tier = get_premium_context(c, auth["guild"])["premium_only"]
            enabled_count = _enabled_count(c, auth["guild"])

            if request.form.get("kick_no_pfp"):
                setting_no_avatar.set(c, auth["guild"], "true")
            else:
                setting_no_avatar.set(c, auth["guild"], "false")

            if (
                request.form.get("kick_min_age")
                and request.form["kick_min_age"].isnumeric()
                and 0 <= int(request.form["kick_min_age"]) < 31
            ):
                setting_minimum_age.set(c, auth["guild"], request.form["kick_min_age"])

            enabled_count = _set_enabled(c, auth["guild"], setting_mrbeast_scam, "mrbeast_scam", free_tier, enabled_count)
            if request.form.get("mrbeast_action") in VALID_ACTIONS:
                setting_mrbeast_action.set(c, auth["guild"], request.form["mrbeast_action"])
            _set_checkbox(c, auth["guild"], setting_mrbeast_dm, "mrbeast_dm")
            _set_checkbox(c, auth["guild"], setting_mrbeast_delete, "mrbeast_delete")

            enabled_count = _set_enabled(c, auth["guild"], setting_flood_enabled, "flood_enabled", free_tier, enabled_count)
            if request.form.get("flood_action") in VALID_ACTIONS:
                setting_flood_action.set(c, auth["guild"], request.form["flood_action"])
            _set_checkbox(c, auth["guild"], setting_flood_dm, "flood_dm")
            _set_checkbox(c, auth["guild"], setting_flood_delete, "flood_delete")
            _set_number(c, auth["guild"], setting_flood_count, "flood_count")
            _set_number(c, auth["guild"], setting_flood_window, "flood_window")

            if message_intent:
                enabled_count = _set_enabled(c, auth["guild"], setting_duplicate_enabled, "duplicate_enabled", free_tier, enabled_count)
                if request.form.get("duplicate_action") in VALID_ACTIONS:
                    setting_duplicate_action.set(c, auth["guild"], request.form["duplicate_action"])
                _set_checkbox(c, auth["guild"], setting_duplicate_dm, "duplicate_dm")
                _set_checkbox(c, auth["guild"], setting_duplicate_delete, "duplicate_delete")
                _set_number(c, auth["guild"], setting_duplicate_count, "duplicate_count")
                _set_number(c, auth["guild"], setting_duplicate_window, "duplicate_window")

                enabled_count = _set_enabled(c, auth["guild"], setting_mentions_enabled, "mentions_enabled", free_tier, enabled_count)
                if request.form.get("mentions_action") in VALID_ACTIONS:
                    setting_mentions_action.set(c, auth["guild"], request.form["mentions_action"])
                _set_checkbox(c, auth["guild"], setting_mentions_dm, "mentions_dm")
                _set_checkbox(c, auth["guild"], setting_mentions_delete, "mentions_delete")
                _set_number(c, auth["guild"], setting_mentions_count, "mentions_count")

                enabled_count = _set_enabled(c, auth["guild"], setting_invite_enabled, "invite_enabled", free_tier, enabled_count)
                if request.form.get("invite_action") in VALID_ACTIONS:
                    setting_invite_action.set(c, auth["guild"], request.form["invite_action"])
                _set_checkbox(c, auth["guild"], setting_invite_dm, "invite_dm")
                _set_checkbox(c, auth["guild"], setting_invite_delete, "invite_delete")
                _set_number(c, auth["guild"], setting_invite_count, "invite_count")
                _set_number(c, auth["guild"], setting_invite_window, "invite_window")

                enabled_count = _set_enabled(c, auth["guild"], setting_caps_enabled, "caps_enabled", free_tier, enabled_count)
                if request.form.get("caps_action") in VALID_ACTIONS:
                    setting_caps_action.set(c, auth["guild"], request.form["caps_action"])
                _set_checkbox(c, auth["guild"], setting_caps_dm, "caps_dm")
                _set_checkbox(c, auth["guild"], setting_caps_delete, "caps_delete")
                _set_number(c, auth["guild"], setting_caps_percentage, "caps_percentage")
                _set_number(c, auth["guild"], setting_caps_min_length, "caps_min_length")

                enabled_count = _set_enabled(c, auth["guild"], setting_emoji_enabled, "emoji_enabled", free_tier, enabled_count)
                if request.form.get("emoji_action") in VALID_ACTIONS:
                    setting_emoji_action.set(c, auth["guild"], request.form["emoji_action"])
                _set_checkbox(c, auth["guild"], setting_emoji_dm, "emoji_dm")
                _set_checkbox(c, auth["guild"], setting_emoji_delete, "emoji_delete")
                _set_number(c, auth["guild"], setting_emoji_count, "emoji_count")
                _set_number(c, auth["guild"], setting_emoji_window, "emoji_window")

            enabled_count = _set_enabled(c, auth["guild"], setting_sticker_enabled, "sticker_enabled", free_tier, enabled_count)
            if request.form.get("sticker_action") in VALID_ACTIONS:
                setting_sticker_action.set(c, auth["guild"], request.form["sticker_action"])
            _set_checkbox(c, auth["guild"], setting_sticker_dm, "sticker_dm")
            _set_checkbox(c, auth["guild"], setting_sticker_delete, "sticker_delete")
            _set_number(c, auth["guild"], setting_sticker_count, "sticker_count")
            _set_number(c, auth["guild"], setting_sticker_window, "sticker_window")

            enabled_count = _set_enabled(c, auth["guild"], setting_joinburst_enabled, "joinburst_enabled", free_tier, enabled_count)
            if request.form.get("joinburst_action") in VALID_ACTIONS:
                setting_joinburst_action.set(c, auth["guild"], request.form["joinburst_action"])
            _set_checkbox(c, auth["guild"], setting_joinburst_dm, "joinburst_dm")
            _set_number(c, auth["guild"], setting_joinburst_count, "joinburst_count")
            _set_number(c, auth["guild"], setting_joinburst_window, "joinburst_window")

            for prefix, timeout_setting, dm_message_setting, reason_setting in DETECTORS:
                if not message_intent and prefix in CONTENT_DETECTORS:
                    continue
                _set_number(c, auth["guild"], timeout_setting, f"{prefix}_timeout")
                _set_text(c, auth["guild"], dm_message_setting, f"{prefix}_dm_message")
                _set_text(c, auth["guild"], reason_setting, f"{prefix}_reason")

        kick_no_pfp = setting_no_avatar.get(c, auth["guild"]) == "true"
        kick_min_age = setting_minimum_age.get(c, auth["guild"])
        mrbeast_scam = setting_mrbeast_scam.get(c, auth["guild"]) == "true"
        mrbeast_action = setting_mrbeast_action.get(c, auth["guild"])
        mrbeast_dm = setting_mrbeast_dm.get(c, auth["guild"]) == "true"
        mrbeast_delete = setting_mrbeast_delete.get(c, auth["guild"]) == "true"

        flood_enabled = setting_flood_enabled.get(c, auth["guild"]) == "true"
        flood_action = setting_flood_action.get(c, auth["guild"])
        flood_dm = setting_flood_dm.get(c, auth["guild"]) == "true"
        flood_delete = setting_flood_delete.get(c, auth["guild"]) == "true"
        flood_count = setting_flood_count.get(c, auth["guild"])
        flood_window = setting_flood_window.get(c, auth["guild"])

        duplicate_enabled = setting_duplicate_enabled.get(c, auth["guild"]) == "true"
        duplicate_action = setting_duplicate_action.get(c, auth["guild"])
        duplicate_dm = setting_duplicate_dm.get(c, auth["guild"]) == "true"
        duplicate_delete = setting_duplicate_delete.get(c, auth["guild"]) == "true"
        duplicate_count = setting_duplicate_count.get(c, auth["guild"])
        duplicate_window = setting_duplicate_window.get(c, auth["guild"])

        mentions_enabled = setting_mentions_enabled.get(c, auth["guild"]) == "true"
        mentions_action = setting_mentions_action.get(c, auth["guild"])
        mentions_dm = setting_mentions_dm.get(c, auth["guild"]) == "true"
        mentions_delete = setting_mentions_delete.get(c, auth["guild"]) == "true"
        mentions_count = setting_mentions_count.get(c, auth["guild"])

        invite_enabled = setting_invite_enabled.get(c, auth["guild"]) == "true"
        invite_action = setting_invite_action.get(c, auth["guild"])
        invite_dm = setting_invite_dm.get(c, auth["guild"]) == "true"
        invite_delete = setting_invite_delete.get(c, auth["guild"]) == "true"
        invite_count = setting_invite_count.get(c, auth["guild"])
        invite_window = setting_invite_window.get(c, auth["guild"])

        caps_enabled = setting_caps_enabled.get(c, auth["guild"]) == "true"
        caps_action = setting_caps_action.get(c, auth["guild"])
        caps_dm = setting_caps_dm.get(c, auth["guild"]) == "true"
        caps_delete = setting_caps_delete.get(c, auth["guild"]) == "true"
        caps_percentage = setting_caps_percentage.get(c, auth["guild"])
        caps_min_length = setting_caps_min_length.get(c, auth["guild"])

        emoji_enabled = setting_emoji_enabled.get(c, auth["guild"]) == "true"
        emoji_action = setting_emoji_action.get(c, auth["guild"])
        emoji_dm = setting_emoji_dm.get(c, auth["guild"]) == "true"
        emoji_delete = setting_emoji_delete.get(c, auth["guild"]) == "true"
        emoji_count = setting_emoji_count.get(c, auth["guild"])
        emoji_window = setting_emoji_window.get(c, auth["guild"])

        sticker_enabled = setting_sticker_enabled.get(c, auth["guild"]) == "true"
        sticker_action = setting_sticker_action.get(c, auth["guild"])
        sticker_dm = setting_sticker_dm.get(c, auth["guild"]) == "true"
        sticker_delete = setting_sticker_delete.get(c, auth["guild"]) == "true"
        sticker_count = setting_sticker_count.get(c, auth["guild"])
        sticker_window = setting_sticker_window.get(c, auth["guild"])

        joinburst_enabled = setting_joinburst_enabled.get(c, auth["guild"]) == "true"
        joinburst_action = setting_joinburst_action.get(c, auth["guild"])
        joinburst_dm = setting_joinburst_dm.get(c, auth["guild"]) == "true"
        joinburst_count = setting_joinburst_count.get(c, auth["guild"])
        joinburst_window = setting_joinburst_window.get(c, auth["guild"])

        template_data = {}
        for prefix, timeout_setting, dm_message_setting, reason_setting in DETECTORS:
            template_data[f"{prefix}_timeout"] = timeout_setting.get(c, auth["guild"])
            template_data[f"{prefix}_dm_message"] = dm_message_setting.get(c, auth["guild"])
            template_data[f"{prefix}_reason"] = reason_setting.get(c, auth["guild"])

        premium = get_premium_context(c, auth["guild"])

    return render_template(
        "anti_raid.html",
        kick_no_pfp=kick_no_pfp,
        kick_min_age=kick_min_age,
        mrbeast_scam=mrbeast_scam,
        mrbeast_action=mrbeast_action,
        mrbeast_dm=mrbeast_dm,
        mrbeast_delete=mrbeast_delete,
        flood_enabled=flood_enabled,
        flood_action=flood_action,
        flood_dm=flood_dm,
        flood_delete=flood_delete,
        flood_count=flood_count,
        flood_window=flood_window,
        duplicate_enabled=duplicate_enabled,
        duplicate_action=duplicate_action,
        duplicate_dm=duplicate_dm,
        duplicate_delete=duplicate_delete,
        duplicate_count=duplicate_count,
        duplicate_window=duplicate_window,
        mentions_enabled=mentions_enabled,
        mentions_action=mentions_action,
        mentions_dm=mentions_dm,
        mentions_delete=mentions_delete,
        mentions_count=mentions_count,
        invite_enabled=invite_enabled,
        invite_action=invite_action,
        invite_dm=invite_dm,
        invite_delete=invite_delete,
        invite_count=invite_count,
        invite_window=invite_window,
        caps_enabled=caps_enabled,
        caps_action=caps_action,
        caps_dm=caps_dm,
        caps_delete=caps_delete,
        caps_percentage=caps_percentage,
        caps_min_length=caps_min_length,
        emoji_enabled=emoji_enabled,
        emoji_action=emoji_action,
        emoji_dm=emoji_dm,
        emoji_delete=emoji_delete,
        emoji_count=emoji_count,
        emoji_window=emoji_window,
        sticker_enabled=sticker_enabled,
        sticker_action=sticker_action,
        sticker_dm=sticker_dm,
        sticker_delete=sticker_delete,
        sticker_count=sticker_count,
        sticker_window=sticker_window,
        joinburst_enabled=joinburst_enabled,
        joinburst_action=joinburst_action,
        joinburst_dm=joinburst_dm,
        joinburst_count=joinburst_count,
        joinburst_window=joinburst_window,
        message_intent=message_intent,
        premium=premium,
        **template_data,
    )