from flask import Flask, redirect, url_for, render_template, \
    request, make_response, Response, Markup, Blueprint, current_app, g

from wrapper.exceptions import *

blueprint_login = Blueprint("login", __name__,
        template_folder="templates")

@blueprint_login.before_request
def before_request():
    g.wrapper = current_app.wrapper
    g.verify_token = current_app.wrapper.dashboard.auth.verify_token
    g.invalidate_token = current_app.wrapper.dashboard.auth.invalidate_token
    g.authenticate = current_app.wrapper.dashboard.auth.authenticate

# @blueprint_login.route("/test", methods=["GET", "POST"])
# def test():
#     print(g.wrapper)
#     return "Hello"

@blueprint_login.route("/logout")
def logout():
    g.invalidate_token()

    rsp = make_response(redirect("/login"))
    rsp.set_cookie("_wrapper_token", "")

    return rsp

@blueprint_login.route("/login", methods=["GET", "POST"])
def login():
    try:
        if g.verify_token():
            print("Already authenticated.")
            return redirect("/")
    except AuthError:
        pass

    auth_failure = False

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        try:
            token = g.authenticate(username, password)

            rsp = make_response(redirect("/"))
            rsp.set_cookie("_wrapper_token", token)

            return rsp
        except AuthError as e:
            auth_failure = str(e)

    return render_template("login.html", auth_failure=auth_failure)
