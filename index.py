#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
pip install flask authlib flask-wtf requests
"""

from flask import (Flask, g, render_template, request, flash, redirect, make_response,
                   url_for as flask_url_for)
import time
import json
import sys
import os
import database
import helper
from authlib.integrations.flask_client import OAuth
import logging
from logging.handlers import RotatingFileHandler
import settings
from flask_wtf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix
import argparse


sys.path.insert(0, os.path.dirname(__file__))
if not os.path.exists(database.temp_dir):
    os.makedirs(database.temp_dir, exist_ok=True)
current_path = os.path.dirname(os.path.realpath(__file__))

IS_LOCAL = os.environ.get('REMOTE_ADDR') == '127.0.0.1' or os.environ.get('SERVER_NAME') == 'localhost'


class HeaderDeduplicateMiddleware:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # Nginx or multiple proxies might double headers like "Host: domain,domain"
        # and "X-Forwarded-Proto: https,https". This deduplicates them.
        for key in ['HTTP_HOST', 'HTTP_X_FORWARDED_FOR', 'HTTP_X_FORWARDED_PROTO', 'HTTP_X_FORWARDED_HOST']:
            value = environ.get(key)
            if value and ',' in value:
                parts = [p.strip() for p in value.split(',')]
                # If all parts are identical, we take just one
                if all(p == parts[0] for p in parts):
                    environ[key] = parts[0]
        return self.app(environ, start_response)


application = Flask(__name__, static_url_path='/static', static_folder='static')
application.wsgi_app = ProxyFix(application.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
application.wsgi_app = HeaderDeduplicateMiddleware(application.wsgi_app)
application.config.update(
    SESSION_COOKIE_SECURE=not IS_LOCAL,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_NAME=settings.APP_NAME,
    SECRET_KEY=settings.APP_SECRET_KEY,
    WTF_CSRF_SECRET_KEY=settings.APP_SECRET_KEY,
    WTF_CSRF_TRUSTED_ORIGINS=[settings.APP_URL],
    WTF_CSRF_SSL_STRICT=True,
    APPLICATION_ROOT='/',
)
csrf = CSRFProtect(application)

# ---------------------- Logging ----------------------
def setup_logger(is_local: bool):
    logger_obj = logging.getLogger()
    logger_obj.setLevel(logging.DEBUG)

    if logger_obj.hasHandlers():
        logger_obj.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt='%Y-%m-%dT%H:%M:%S'
    )

    if is_local:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger_obj.addHandler(console_handler)
    else:
        file_handler = RotatingFileHandler(
            os.path.join(os.path.dirname(__file__), 'app.log'),
            maxBytes=65535,
            backupCount=1
        )
        file_handler.setFormatter(formatter)
        logger_obj.addHandler(file_handler)

    return logger_obj

logger = setup_logger(IS_LOCAL)


# ---------------------- Helpers ----------------------
def safe_url_for(endpoint, **values):
    """
    Clean up CGI SCRIPT_NAME issues for url_for and
    automatically prefix URLs with the current language.
    """
    # 1. Generate a Flask URL
    url = flask_url_for(endpoint, **values)

    # 2. Fix SCRIPT_NAME issues (your logic)
    script_name = request.environ.get('SCRIPT_NAME', '')
    if script_name and url.startswith(script_name):
        url = url[len(script_name):] or '/'

    return url

def register_google_oauth():
    """
    Load client secrets and register OAuth for Google.
    """
    client_secrets_path = os.path.join(current_path, settings.CLIENT_SECRETS_FILE)
    with open(client_secrets_path) as f:
        client_secrets = json.load(f)['web']

    oauth = OAuth(application)
    return oauth.register(
        name='google',
        client_id=client_secrets['client_id'],
        client_secret=client_secrets['client_secret'],
        access_token_url=client_secrets['token_uri'],
        authorize_url=client_secrets['auth_uri'],
        api_base_url='https://www.googleapis.com/oauth2/v1/',
        userinfo_endpoint='https://www.googleapis.com/oauth2/v3/userinfo',
        client_kwargs={'scope': 'email'},
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration'
    )

# ---------------------- OAuth ----------------------
google = None
client_secrets_path = os.path.join(current_path, settings.CLIENT_SECRETS_FILE)
if os.path.isfile(client_secrets_path):
    try:
        google = register_google_oauth()
    except Exception as e:
        logger.error(f"Failed to register Google OAuth: {e}")


@application.before_request
def before_request():
    g.db = database.open_db()


@application.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        database.close_db(g.db)


@application.route('/', methods=['GET'])
def index():
    resp = make_response(render_template('home.html', title=settings.APP_TITLE, url_for=safe_url_for))

    # Add no-cache headers
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"

    return resp


@application.route('/authorize')
def authorize():
    auth_url = safe_url_for('oauth2callback')
    return google.authorize_redirect(f"https://{request.host}{auth_url}")


@application.route('/login', methods=['GET'])
def login():
    if application.debug:
        token = helper.generate_token()
        user_email = settings.SUPER_ADMIN
        user = database.get_user(connection=g.db, email=user_email)
        if not user:
            database.add_user(connection=g.db, email=user_email, token=token)
        database.update_user(connection=g.db, email=user_email, token=token, authorized=2)

        response = make_response(redirect(safe_url_for('settings_page')))
        response.set_cookie('token', token, max_age=settings.MAX_COOKIE_AGE, expires=time.time() + settings.MAX_COOKIE_AGE)
        return response

    return render_template('login.html', title=settings.APP_TITLE, url_for=safe_url_for)


@application.route('/logout')
def logout():
    token = request.cookies.get('token')
    if token:
        user = database.get_user(connection=g.db, token=token)
        if user:
            database.update_user(connection=g.db, email=user["email"], token=helper.generate_token())

    response = make_response(redirect(safe_url_for('index')))
    response.set_cookie('token', '', expires=0)
    return response


@application.route('/oauth2callback')
def oauth2callback():
    global google

    if application.debug:
        # Just redirect to settings, since login is automatic in /login for debug
        return redirect(safe_url_for('settings_page'))

    try:
        google.authorize_access_token()
        resp = google.get('userinfo')
        user_info = resp.json()
        email = user_info["email"]
        picture = user_info.get("picture")

        token = helper.generate_token()

        user = database.get_user(connection=g.db, email=email)
        if not user:
            # New user: sign up as unauthorized and notify the admin(s)
            database.add_user(connection=g.db, email=email, token=token)
            database.update_user(connection=g.db, email=email, picture=picture)
            user = database.get_user(connection=g.db, email=email)

            admins = database.get_user(connection=g.db, authorized=2)
            for admin in admins:
                body = (
                    f"A new user tried to log in to {settings.APP_TITLE}: {email}\n\n"
                    f"Enable them here: {request.host_url.rstrip('/')}{safe_url_for('settings_page')}"
                )
                helper.send_email(
                    recipient=admin.get('email'),
                    subject=f"New user pending approval on {settings.APP_TITLE}",
                    body=body
                )
        else:
            database.update_user(connection=g.db, email=email, token=token, picture=picture)
            user = database.get_user(connection=g.db, email=email)

        if user.get("authorized", 0) > 0:
            response = make_response(redirect(safe_url_for('settings_page')))
            response.set_cookie('token', token, max_age=settings.MAX_COOKIE_AGE, expires=time.time() + settings.MAX_COOKIE_AGE)
        else:
            flash("Your account has not been authorized yet. The admin has been notified.")
            response = redirect(safe_url_for("login"))
            response.set_cookie('token', '', expires=0)

    except Exception as e:
        logger.exception(f"OAuth2 callback error {e}")
        # Restart the login flow
        google = register_google_oauth()

        response = redirect(safe_url_for("login"))
        response.set_cookie('token', '', expires=0)

    return response


@application.route('/settings', methods=['GET'])
def settings_page():
    token = request.cookies.get('token')
    if not token:
        return redirect(safe_url_for('login'))

    user = database.get_user(connection=g.db, token=token)
    if not user:
        return redirect(safe_url_for('login'))

    if user["authorized"] < 1:
        flash("Your account has not been authorized yet.")
        return redirect(safe_url_for('login'))

    is_admin = user["authorized"] > 1
    unauthorized_users = []
    authorized_users = []

    if is_admin:
        unauthorized_users = sorted(
            database.get_user(connection=g.db, authorized=0),
            key=lambda u: u["email"].lower()
        )

        authorized_users = (
            database.get_user(connection=g.db, authorized=1)
            + database.get_user(connection=g.db, authorized=2)
        )
        # put current user last, others alphabetical by email
        authorized_users = sorted(
            authorized_users,
            key=lambda u: (u["email"].lower() == user["email"].lower(), u["email"].lower())
        )

    return render_template(
        'settings.html',
        user=user,
        admin=is_admin,
        unauthorized_users=unauthorized_users,
        authorized_users=authorized_users,
        title=settings.APP_TITLE,
        url_for=safe_url_for
    )


@application.route('/settings/users', methods=['POST'])
def settings_users_post():
    token = request.cookies.get('token')
    if not token:
        return redirect(safe_url_for('login'))

    user = database.get_user(connection=g.db, token=token)
    if not user or user["authorized"] < 2:
        flash("You are not authorized to perform this action.")
        return redirect(safe_url_for('settings_page'))

    email = request.form.get('email')
    action = request.form.get('action')

    if not email or not action:
        return redirect(safe_url_for('settings_page'))

    if action == 'authorize':
        database.update_user(connection=g.db, email=email, authorized=1)
    elif action == 'make_admin':
        database.update_user(connection=g.db, email=email, authorized=2)
    elif action == 'remove':
        database.delete_user(connection=g.db, email=email)

    database.sync_temp_db_to_disk(connection=g.db)

    return redirect(safe_url_for('settings_page'))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--local', action='store_true', help='Run without Google login for local development')
    cmdargs = parser.parse_args()

    IS_LOCAL = cmdargs.local
    logger = setup_logger(IS_LOCAL)
    database.setup_initial_db()
    application.run(debug=IS_LOCAL, use_reloader=True, port=8020)
