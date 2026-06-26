from flask import Blueprint, render_template

main_page_bp = Blueprint("main_page", __name__, template_folder='website')

@main_page_bp.route("/")
def index():
    return render_template("index.html")

@main_page_bp.route("/features")
def features():
    return render_template("features.html")

@main_page_bp.route("/tos")
def tos():
    return render_template("tos.html")

@main_page_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")

@main_page_bp.route("/support-me")
def support_me():
    return render_template("support-me.html")

@main_page_bp.route("/support-bot")
def support_bot():
    return render_template("support-bot.html")
