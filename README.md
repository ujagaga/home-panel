# Home Panel

Python3 Flask home panel app.

The home page shows a full-screen black background with a digital clock (using the browser's own
time zone). There is no navigation on the home page — hover over the top-right 5px screen edge to
reveal a hidden settings icon.

Login is done using Google OAuth2, so user emails must be Google accounts. There is no password.

# User accounts

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
A reverse tunnel should provide its own SSL certificate to support HTTPS, which is necessary for
Google OAuth2 authentication.

## Note
- The admin email is set in `settings.py` (`SUPER_ADMIN`) and is automatically enabled.
- The SQLite database will be located in this folder, but at startup it will be copied to
  `/dev/shm/`. This is the shared memory space in RAM and will prevent storage wear on a Raspberry
  Pi SD card due to frequent writes. When you save any settings from the UI, the temporary database
  in shared memory will be copied over the main database to persist the changes.
