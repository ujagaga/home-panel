#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
pip install flask authlib flask-wtf requests
"""

from flask import (Flask, g, render_template, request, flash, redirect, make_response,
                   url_for as flask_url_for, abort, jsonify)
import time
import json
import re
import sys
import os
import requests
from datetime import datetime
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


# Curated clock fonts. Value is the Google Fonts family query param, or None for the
# system default (no external font to load).
CLOCK_FONTS = {
    "Courier New": None,
    "Orbitron": "Orbitron",
    "Share Tech Mono": "Share+Tech+Mono",
    "VT323": "VT323",
    "Major Mono Display": "Major+Mono+Display",
    "Audiowide": "Audiowide",
    "Chakra Petch": "Chakra+Petch",
}
DEFAULT_CLOCK_FONT = "Courier New"

CLOCK_FONT_WEIGHTS = {
    300: "Light",
    400: "Regular",
    500: "Medium",
    600: "Semi-Bold",
    700: "Bold",
    800: "Extra Bold",
    900: "Black",
}
DEFAULT_CLOCK_FONT_WEIGHT = 400

# Curated tileable floral background patterns for the clock text. Each has its own
# native tile size (px) used for background-size so it repeats cleanly.
CLOCK_PATTERNS = {
    "Solid": {"template": "floral2", "tile": 60},
    "Daisy Grid": {"template": "floral1", "tile": 80},
    "Clover Bloom": {"template": "floral2", "tile": 60},
    "Vine Blossom": {"template": "floral3", "tile": 100},
}
DEFAULT_CLOCK_PATTERN = "Daisy Grid"
DEFAULT_CLOCK_PATTERN_COLOR = "#e8708a"
DEFAULT_CLOCK_PATTERN_BG_COLOR = "#000000"

# Percentage of each pattern's native tile size.
CLOCK_PATTERN_SIZES = {
    50: "Small",
    100: "Medium",
    150: "Large",
    200: "Extra Large",
}
DEFAULT_CLOCK_PATTERN_SIZE = 100

# Same percentage scale, reused for sizing the weather widget.
WEATHER_SIZES = CLOCK_PATTERN_SIZES
DEFAULT_WEATHER_SIZE = 100

HEX_COLOR_RE = re.compile(r'^#[0-9a-fA-F]{6}$')

# ---------------------- Weather ----------------------
WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_CACHE_SECONDS = 30 * 60
WEATHER_LOOKAHEAD_HOURS = 8

NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
PLACE_NAME_SUFFIX_RE = re.compile(r'^City of\s+|\s+(Municipality|District|County|Region|Province)$')


def reverse_geocode_city(lat, lon):
    """Best-effort city/town name for a location, or None. Tried in order of
    specificity; administrative-boundary wording ("City of ..", ".. Municipality")
    is stripped since Nominatim's naming varies by country."""
    try:
        resp = requests.get(NOMINATIM_REVERSE_URL, params={
            "lat": lat,
            "lon": lon,
            "format": "json",
            "zoom": 14,
            "addressdetails": 1,
            "accept-language": "en",
        }, headers={"User-Agent": f"{settings.APP_TITLE} weather widget"}, timeout=10)
        resp.raise_for_status()
        address = resp.json().get("address", {})

        for key in ("town", "village", "city", "municipality", "county"):
            if address.get(key):
                return PLACE_NAME_SUFFIX_RE.sub('', address[key]).strip()
    except Exception as e:
        logger.exception(f"Reverse geocoding failed: {e}")

    return None

WEATHER_CODE_CATEGORY = {
    0: "Clear", 1: "Mostly Clear", 2: "Partly Cloudy", 3: "Cloudy",
    45: "Fog", 48: "Fog",
    51: "Drizzle", 53: "Drizzle", 55: "Drizzle", 56: "Drizzle", 57: "Drizzle",
    61: "Rain", 63: "Rain", 65: "Rain", 66: "Rain", 67: "Rain",
    71: "Snow", 73: "Snow", 75: "Snow", 77: "Snow", 85: "Snow", 86: "Snow",
    80: "Rain", 81: "Rain", 82: "Rain",
    95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm",
}
WEATHER_ICONS = {
    "Clear": "☀️", "Mostly Clear": "🌤️", "Partly Cloudy": "⛅", "Cloudy": "☁️",
    "Fog": "🌫️", "Drizzle": "🌦️", "Rain": "🌧️", "Snow": "❄️", "Thunderstorm": "⛈️",
}
WEATHER_DEFAULT_CATEGORY = "Cloudy"
PRECIP_CATEGORIES = {"Drizzle", "Rain", "Thunderstorm", "Snow"}

_weather_cache = {}


def fetch_weather(lat, lon):
    cache_key = (round(lat, 2), round(lon, 2))
    cached = _weather_cache.get(cache_key)
    now = time.time()
    if cached and now - cached["ts"] < WEATHER_CACHE_SECONDS:
        return cached["data"]

    try:
        resp = requests.get(WEATHER_API_URL, params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,weather_code",
            "hourly": "weather_code",
            "forecast_days": 2,
            "timezone": "auto",
        }, timeout=10)
        resp.raise_for_status()
        raw = resp.json()

        current_time = datetime.fromisoformat(raw["current"]["time"])
        current_category = WEATHER_CODE_CATEGORY.get(raw["current"]["weather_code"], WEATHER_DEFAULT_CATEGORY)

        current_is_precip = current_category in PRECIP_CATEGORIES

        change = None
        ahead = 0
        for t_str, code in zip(raw["hourly"]["time"], raw["hourly"]["weather_code"]):
            t = datetime.fromisoformat(t_str)
            if t <= current_time:
                continue
            ahead += 1
            if ahead > WEATHER_LOOKAHEAD_HOURS:
                break
            category = WEATHER_CODE_CATEGORY.get(code, WEATHER_DEFAULT_CATEGORY)
            category_is_precip = category in PRECIP_CATEGORIES

            if category_is_precip and not current_is_precip:
                change = {"category": category, "icon": WEATHER_ICONS.get(category, "☁️"),
                          "at": t.strftime("%H:%M"), "kind": "starting"}
                break
            if current_is_precip and not category_is_precip:
                change = {"category": current_category, "icon": WEATHER_ICONS.get(current_category, "☁️"),
                          "at": t.strftime("%H:%M"), "kind": "stopping"}
                break

        data = {
            "available": True,
            "current": {
                "temp": round(raw["current"]["temperature_2m"]),
                "category": current_category,
                "icon": WEATHER_ICONS.get(current_category, "☁️"),
            },
            "change": change,
        }
        _weather_cache[cache_key] = {"data": data, "ts": now}
        return data
    except Exception as e:
        logger.exception(f"Weather fetch failed: {e}")
        return cached["data"] if cached else {"available": False}


@application.before_request
def before_request():
    g.db = database.open_db()


@application.teardown_request
def teardown_request(exception):
    if hasattr(g, 'db'):
        database.close_db(g.db)


def require_authorized_user():
    """Returns the logged-in user dict, or None (flashing a message if they are pending approval)."""
    token = request.cookies.get('token')
    if not token:
        return None

    user = database.get_user(connection=g.db, token=token)
    if not user:
        return None

    if user["authorized"] < 1:
        flash("Your account has not been authorized yet.")
        return None

    return user


def resolve_clock_display(user):
    """Builds the home.html template vars for a user's clock appearance settings."""
    clock_font = user.get("clock_font") or DEFAULT_CLOCK_FONT
    clock_font_weight = user.get("clock_font_weight") or DEFAULT_CLOCK_FONT_WEIGHT
    clock_pattern = user.get("clock_pattern") or DEFAULT_CLOCK_PATTERN
    if clock_pattern not in CLOCK_PATTERNS:
        clock_pattern = DEFAULT_CLOCK_PATTERN
    clock_pattern_color = user.get("clock_pattern_color") or DEFAULT_CLOCK_PATTERN_COLOR
    clock_pattern_bg_color = user.get("clock_pattern_bg_color") or DEFAULT_CLOCK_PATTERN_BG_COLOR
    if clock_pattern == "Solid":
        clock_pattern_bg_color = clock_pattern_color
    clock_pattern_size = user.get("clock_pattern_size") or DEFAULT_CLOCK_PATTERN_SIZE
    if clock_pattern_size not in CLOCK_PATTERN_SIZES:
        clock_pattern_size = DEFAULT_CLOCK_PATTERN_SIZE

    return {
        "clock_font": clock_font,
        "clock_font_weight": clock_font_weight,
        "google_font_query": CLOCK_FONTS.get(clock_font),
        "clock_pattern": clock_pattern,
        "clock_pattern_color": clock_pattern_color,
        "clock_pattern_bg_color": clock_pattern_bg_color,
        "pattern_tile": round(CLOCK_PATTERNS[clock_pattern]["tile"] * clock_pattern_size / 100),
    }


@application.route('/', methods=['GET'])
def index():
    user = require_authorized_user()
    if not user:
        return redirect(safe_url_for('login'))

    resp = make_response(render_template(
        'home.html',
        title=settings.APP_TITLE,
        url_for=safe_url_for,
        show_settings_icon=True,
        public_key=None,
        weather_size=user.get("weather_size") or DEFAULT_WEATHER_SIZE,
        **resolve_clock_display(user)
    ))

    # Add no-cache headers
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"

    return resp


@application.route('/u/<key>', methods=['GET'])
def public_home(key):
    """Shows a user's clock, styled with their own settings, without requiring login."""
    user = next(
        (u for u in database.get_user(connection=g.db) if helper.email_to_key(u["email"]) == key),
        None
    )
    if not user or user["authorized"] < 1:
        abort(404)

    return render_template(
        'home.html',
        title=settings.APP_TITLE,
        url_for=safe_url_for,
        show_settings_icon=False,
        public_key=key,
        weather_size=user.get("weather_size") or DEFAULT_WEATHER_SIZE,
        **resolve_clock_display(user)
    )


@application.route('/weather.json')
def weather_json():
    key = request.args.get('key')
    if key:
        user = next(
            (u for u in database.get_user(connection=g.db) if helper.email_to_key(u["email"]) == key),
            None
        )
        if not user or user["authorized"] < 1:
            return jsonify({"available": False}), 404
    else:
        user = require_authorized_user()
        if not user:
            return jsonify({"available": False}), 401

    lat = user.get("weather_lat")
    lon = user.get("weather_lon")
    if lat is None or lon is None:
        return jsonify({"available": False})

    # Copy: fetch_weather() may return the shared cached dict, and different users
    # can round to the same cache key while having different saved city names.
    data = dict(fetch_weather(lat, lon))
    data["city"] = user.get("weather_city")
    return jsonify(data)


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

        response = make_response(redirect(safe_url_for('index')))
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
        # Just redirect to index, since login is automatic in /login for debug
        return redirect(safe_url_for('index'))

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
            response = make_response(redirect(safe_url_for('index')))
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


@application.route('/pattern.svg')
def pattern_svg():
    name = request.args.get('name', DEFAULT_CLOCK_PATTERN)
    color = request.args.get('color', DEFAULT_CLOCK_PATTERN_COLOR)
    bg_color = request.args.get('bg_color', DEFAULT_CLOCK_PATTERN_BG_COLOR)

    pattern = CLOCK_PATTERNS.get(name, CLOCK_PATTERNS[DEFAULT_CLOCK_PATTERN])
    if not HEX_COLOR_RE.match(color):
        color = DEFAULT_CLOCK_PATTERN_COLOR
    if not HEX_COLOR_RE.match(bg_color):
        bg_color = DEFAULT_CLOCK_PATTERN_BG_COLOR

    resp = make_response(render_template(f"patterns/{pattern['template']}.svg", color=color, background_color=bg_color))
    resp.headers["Content-Type"] = "image/svg+xml"
    return resp


@application.route('/settings', methods=['GET'])
def settings_page():
    user = require_authorized_user()
    if not user:
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
        clock_fonts=CLOCK_FONTS,
        clock_font=user.get("clock_font") or DEFAULT_CLOCK_FONT,
        clock_font_weights=CLOCK_FONT_WEIGHTS,
        clock_font_weight=user.get("clock_font_weight") or DEFAULT_CLOCK_FONT_WEIGHT,
        clock_patterns=CLOCK_PATTERNS,
        clock_pattern=user.get("clock_pattern") or DEFAULT_CLOCK_PATTERN,
        clock_pattern_color=user.get("clock_pattern_color") or DEFAULT_CLOCK_PATTERN_COLOR,
        clock_pattern_bg_color=user.get("clock_pattern_bg_color") or DEFAULT_CLOCK_PATTERN_BG_COLOR,
        clock_pattern_sizes=CLOCK_PATTERN_SIZES,
        clock_pattern_size=user.get("clock_pattern_size") or DEFAULT_CLOCK_PATTERN_SIZE,
        designated_link=f"{request.host_url.rstrip('/')}{safe_url_for('public_home', key=helper.email_to_key(user['email']))}",
        weather_lat=user.get("weather_lat"),
        weather_lon=user.get("weather_lon"),
        weather_sizes=WEATHER_SIZES,
        weather_size=user.get("weather_size") or DEFAULT_WEATHER_SIZE,
        title=settings.APP_TITLE,
        url_for=safe_url_for
    )


@application.route('/settings/weather', methods=['POST'])
def settings_weather_post():
    user = require_authorized_user()
    if not user:
        return redirect(safe_url_for('login'))

    try:
        size = int(request.form.get('weather_size'))
    except (TypeError, ValueError):
        size = DEFAULT_WEATHER_SIZE
    if size in WEATHER_SIZES:
        database.update_user(connection=g.db, email=user["email"], weather_size=size)

    lat_raw = request.form.get('weather_lat', '').strip()
    lon_raw = request.form.get('weather_lon', '').strip()

    if not lat_raw or not lon_raw:
        database.set_weather_location(connection=g.db, email=user["email"], lat=None, lon=None)
    else:
        try:
            lat = float(lat_raw)
            lon = float(lon_raw)
        except ValueError:
            flash("Invalid coordinates.")
            return redirect(safe_url_for('settings_page'))

        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            flash("Coordinates out of range.")
            return redirect(safe_url_for('settings_page'))

        # Only hit the geocoder when the location actually changed.
        if lat == user.get("weather_lat") and lon == user.get("weather_lon") and user.get("weather_city"):
            city = user.get("weather_city")
        else:
            city = reverse_geocode_city(lat, lon)

        database.set_weather_location(connection=g.db, email=user["email"], lat=lat, lon=lon, city=city)

    database.sync_temp_db_to_disk(connection=g.db)
    return redirect(safe_url_for('settings_page'))


@application.route('/settings/clock_font', methods=['POST'])
def settings_clock_font_post():
    user = require_authorized_user()
    if not user:
        return redirect(safe_url_for('login'))

    font = request.form.get('clock_font')
    try:
        weight = int(request.form.get('clock_font_weight'))
    except (TypeError, ValueError):
        weight = DEFAULT_CLOCK_FONT_WEIGHT

    pattern = request.form.get('clock_pattern')
    color = request.form.get('clock_pattern_color') or DEFAULT_CLOCK_PATTERN_COLOR
    if not HEX_COLOR_RE.match(color):
        color = DEFAULT_CLOCK_PATTERN_COLOR

    bg_color = request.form.get('clock_pattern_bg_color') or DEFAULT_CLOCK_PATTERN_BG_COLOR
    if not HEX_COLOR_RE.match(bg_color):
        bg_color = DEFAULT_CLOCK_PATTERN_BG_COLOR
    if pattern == "Solid":
        bg_color = color

    try:
        size = int(request.form.get('clock_pattern_size'))
    except (TypeError, ValueError):
        size = DEFAULT_CLOCK_PATTERN_SIZE

    if (font in CLOCK_FONTS and weight in CLOCK_FONT_WEIGHTS and pattern in CLOCK_PATTERNS
            and size in CLOCK_PATTERN_SIZES):
        database.update_user(connection=g.db, email=user["email"], clock_font=font, clock_font_weight=weight,
                              clock_pattern=pattern, clock_pattern_color=color, clock_pattern_bg_color=bg_color,
                              clock_pattern_size=size)
        database.sync_temp_db_to_disk(connection=g.db)

    return redirect(safe_url_for('settings_page'))


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
