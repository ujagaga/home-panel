# Home Panel

Python3 Flask app that shows a full-screen digital clock, with per-user appearance settings and an
optional weather widget and an image slideshow from a configured Google Drive folder. 
Login is done using Google OAuth2, so user emails must be Google accounts
— there is no password.

The purpose is mainly to provide a large customizable clock that can be displayed in a web browser,
so usable on an old smartphone, tablet, smart TV. More importantly, it is open source, 
so you can fork it and adjust to your wim.

A deployed app is available at 
https://homepanel.ujagaga.in.rs/

## Home page

- Full-screen black background with a 24h digital clock (`HH:MM`, blinking colon), using the
  browser's own time zone. Requires login.
- No navigation bar. A settings icon sits mostly off-screen at the top-right corner (only its
  border pokes into view) and slides fully into view on hover.
- If a location is configured (see Weather below), a small widget in the top-left corner shows the
  city, current temperature/condition, and — only if rain or snow is about to start or stop within
  the next 8 hours — a second line saying when.
- Each user gets a "Designated Link" (shown on the settings page) of the form `/u/<code>` that
  shows their clock and weather with their own settings, with no login required. The code is a
  short, non-secret, deterministic identifier derived from the user's email (not a hash of
  anything sensitive — don't rely on it being unguessable).

## Settings page

Reached via the gear icon; requires login.

- **Clock Settings**: font (a curated list of Google Fonts, loaded on demand), weight, a tileable
  background texture for the clock digits (including a "Solid" option), its color and background
  color, and its size — with a live preview next to the controls.
- **Weather**: paste a Google Maps link (the lat/lon are extracted automatically and shown in
  editable fields — you can also just type coordinates directly), and a size for the widget. The
  city name is reverse-geocoded automatically via OpenStreetMap's Nominatim and shown above the
  temperature. Leave both coordinate fields blank and save to remove the widget.
- **Slideshow**: paste a Google Drive folder link (shared as "Anyone with the link") and an Enable
  switch. When on, the clock and weather shrink to the left third of the screen and the folder's
  images rotate through the rest, scaled to fit. Requires `GOOGLE_DRIVE_API_KEY` in `settings.py`
  (see `settings.py.example`) — without it the switch has no effect.
- **Dim Display**: a start/end hour and a strength, dimming the whole screen with a black overlay
  during those hours (e.g. for use overnight).
- **User management** (admin only): approve or remove pending users, promote users to admin. Admins
  also get a "Set as Guest Default" button next to the Designated Link, which copies their current
  clock/weather/dim settings to what's shown to anyone who isn't logged in.

## User accounts

One admin account is set as `SUPER_ADMIN` in `settings.py` and is authorized automatically. Any
other user who opens the settings page is asked to sign in with Google. On their first login they
are added to the database as "Unauthorized" and an email is sent to the admin so they know to
enable the new user from the settings page. Once authorized, the admin can promote users to admin
or remove them.

# How to start

You might need to create a virtual python environment and install python libraries:

	pip install flask authlib flask-wtf requests gunicorn

This can be done automatically by running the `install.sh`. Before you do, make a copy of the
`settings.py.example` and rename it to `settings.py`. Then adjust the info in it according to your
needs.

To enable Google OAuth2 login, create an application on Google Cloud Console, activate the OAuth2
API and download the client secrets file. Rename it to match `CLIENT_SECRETS_FILE` in `settings.py`
(`client_secret.json` by default) and place it in this folder.

Deploy this on a Raspberry Pi, dedicated hosting, Oracle cloud instance or any other computer. If
you deploy on a local computer, you will need to make a reverse HTTP tunnel or provide a public IP.
A reverse tunnel — or a reverse proxy like nginx in front of gunicorn — should provide its own SSL
certificate to support HTTPS, which is necessary for Google OAuth2 authentication. `run_server.sh`
runs gunicorn bound to `127.0.0.1`, so a reverse proxy is expected to be the public-facing side.

For local development without a real Google login, run `python index.py --local` and use
`http://127.0.0.1:8020` — this auto-authorizes you as `SUPER_ADMIN` and skips the OAuth flow.

## Note
- The admin email is set in `settings.py` (`SUPER_ADMIN`) and is automatically enabled.
- The weather widget uses Open-Meteo (forecast) and Nominatim (reverse geocoding for the city
  name), both free and requiring no API key. Be considerate of their usage policies if you deploy
  this for many users.
- The SQLite database will be located in this folder, but at startup it will be copied to
  `/dev/shm/`. This is the shared memory space in RAM and will prevent storage wear on a Raspberry
  Pi SD card due to frequent writes. When you save any settings from the UI, the temporary database
  in shared memory will be copied over the main database to persist the changes. Schema changes
  (new settings columns) are applied automatically to both copies on every service restart, so a
  `git pull` + restart is enough after an update — no manual migration needed.
