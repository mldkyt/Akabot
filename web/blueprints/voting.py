import datetime
import hashlib
import hmac
import os

from flask import Blueprint, request
from sqlalchemy import select
from sqlalchemy.sql import insert, update

from database import engine, vote_points
from logger import akabot_logger
from web.webutils.quick_response import quick_response

voting_bp = Blueprint("voting", __name__, template_folder="templates")


def verify_webhook(raw_body: bytes, signature: str, secret: str) -> bool:
    try:
        parts = dict(part.split("=", 1) for part in signature.split(","))

        timestamp = parts["t"]
        received_sig = parts["v1"]
    except (ValueError, KeyError):
        akabot_logger.warning("Failed to parse top.gg webhook signature")
        return False

    payload = timestamp.encode() + b"." + raw_body

    expected_sig = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_sig, received_sig)


@voting_bp.route("/webhooks/topgg", methods=["POST"])
def top_gg_vote_webhook():
    raw_body = request.get_data()

    signature = request.headers.get("x-topgg-signature")

    if not signature:
        return quick_response("Missing signature", 401)

    if not verify_webhook(raw_body, signature, os.getenv("TOPGG_WEBHOOK_SECRET")):
        return quick_response("Invalid signature", 401)

    data = request.get_json()

    if data["type"] == "vote.create":
        with engine.begin() as c:
            existing = c.execute(
                select(vote_points).where(
                    vote_points.c.uid == data["data"]["user"]["platform_id"]
                )
            ).fetchone()
            if existing:
                c.execute(
                    update(vote_points)
                    .where(vote_points.c.uid == data["data"]["user"]["platform_id"])
                    .values(
                        points=vote_points.c.points + data["data"]["weight"],
                        last_vote=datetime.datetime.now(datetime.UTC),
                    )
                )
            else:
                c.execute(
                    insert(vote_points).values(
                        uid=data["data"]["user"]["platform_id"],
                        points=data["data"]["weight"],
                        last_vote=datetime.datetime.now(datetime.UTC),
                    )
                )
    elif data["type"] == "webhook.test" and os.getenv("DEVEL", "0") == "1":
        with engine.begin() as c:
            existing = c.execute(
                select(vote_points).where(
                    vote_points.c.uid == data["data"]["user"]["platform_id"]
                )
            ).fetchone()
            if existing:
                c.execute(
                    update(vote_points)
                    .where(vote_points.c.uid == data["data"]["user"]["platform_id"])
                    .values(
                        points=vote_points.c.points + 1,
                        last_vote=datetime.datetime.now(datetime.UTC),
                    )
                )
            else:
                c.execute(
                    insert(vote_points).values(
                        uid=data["data"]["user"]["platform_id"],
                        points=1,
                        last_vote=datetime.datetime.now(datetime.UTC),
                    )
                )

    return "", 204
