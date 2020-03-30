from flask import Flask, redirect, url_for, render_template, \
    request, make_response, Response, Markup, Blueprint, current_app, g

from wrapper.exceptions import *

blueprint_admin = Blueprint("admin", __name__,
        template_folder="templates")

@blueprint_admin.before_request
def before_request():
    g.wrapper = current_app.wrapper
    g.verify_token = current_app.wrapper.dashboard.auth.verify_token

    try:
        g.username = g.verify_token()
    except AuthError:
        return redirect("/login")

@blueprint_admin.route("/", methods=["GET"])
def landing():
    return render_template("landing.html")
