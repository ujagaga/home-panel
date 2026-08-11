import sys
import sqlite3
import settings
import helper
import logging
import time
import os
import shutil


logger = logging.getLogger(__name__)
script_dir = os.path.dirname(os.path.abspath(__file__))
persist_db = os.path.join(script_dir, settings.DB_NAME)
temp_dir = os.path.join("/dev", "shm", settings.APP_TITLE)
temp_db = os.path.join(temp_dir, settings.DB_NAME)


def check_table_exists(connection, tablename):
    cursor = connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (tablename,))
    data = cursor.fetchone()
    result = bool(data)
    cursor.close()
    return result

def init_database(connection):
    cursor = connection.cursor()

    if not check_table_exists(connection, "users"):
        sql = """
           CREATE TABLE users (
               email TEXT NOT NULL UNIQUE,
               token TEXT UNIQUE,
               picture TEXT,
               authorized INTEGER DEFAULT 0,
               last_seen TEXT,
               clock_font TEXT,
               clock_font_weight INTEGER,
               clock_pattern TEXT,
               clock_pattern_color TEXT,
               clock_pattern_bg_color TEXT,
               clock_pattern_size INTEGER,
               weather_lat REAL,
               weather_lon REAL,
               weather_size INTEGER,
               weather_city TEXT
           );
           """
        cursor.execute(sql)
        connection.commit()

        # Insert super admin user here
        insert_sql = """
            INSERT INTO users (email, authorized)
            VALUES (?, ?)
        """
        cursor.execute(insert_sql, (settings.SUPER_ADMIN, 2))  # 1 = authorized as user, 2 = admin
        connection.commit()
    else:
        # Migrate older databases that predate these columns
        cursor.execute("PRAGMA table_info(users);")
        columns = [row[1] for row in cursor.fetchall()]
        if "clock_font" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN clock_font TEXT;")
            connection.commit()
        if "clock_font_weight" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN clock_font_weight INTEGER;")
            connection.commit()
        if "clock_pattern" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN clock_pattern TEXT;")
            connection.commit()
        if "clock_pattern_color" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN clock_pattern_color TEXT;")
            connection.commit()
        if "clock_pattern_bg_color" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN clock_pattern_bg_color TEXT;")
            connection.commit()
        if "clock_pattern_size" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN clock_pattern_size INTEGER;")
            connection.commit()
        if "weather_lat" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN weather_lat REAL;")
            connection.commit()
        if "weather_lon" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN weather_lon REAL;")
            connection.commit()
        if "weather_size" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN weather_size INTEGER;")
            connection.commit()
        if "weather_city" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN weather_city TEXT;")
            connection.commit()

    cursor.close()


def open_db(db_path=temp_db):
    if not os.path.isfile(temp_db):
        os.makedirs(temp_dir, exist_ok=True)
        if os.path.isfile(persist_db):
            shutil.copy2(persist_db, temp_db)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def close_db(connection):
    connection.close()


def add_user(connection, email: str, token: str):
    sql = "INSERT OR REPLACE INTO users (email, token) VALUES (?, ?);"

    try:
        connection.execute(sql, (email, token))
        connection.commit()
    except Exception as exc:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.exception(f"ERROR adding user to db on line {exc_tb.tb_lineno}!\n\t{exc}")


def delete_user(connection, email: str):
    sql = "DELETE FROM users WHERE email = ?;"

    try:
        connection.execute(sql, (email,))
        connection.commit()
    except Exception as exc:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.exception(f"ERROR adding user to db on line {exc_tb.tb_lineno}!\n\t{exc}")


def get_user(connection, email: str = None, token: str = None, authorized: int = None):
    one = True
    if email:
        sql = "SELECT * FROM users WHERE email = ?;"
        params = (email,)
    elif token:
        sql = "SELECT * FROM users WHERE token = ?;"
        params = (token,)
    elif authorized is not None:
        sql = "SELECT * FROM users WHERE authorized = ?;"
        params = (authorized,)
        one = False
    else:
        sql = "SELECT * FROM users;"
        params = ()
        one = False

    user = None
    try:
        cursor = connection.cursor()
        cursor.execute(sql, params)
        if one:
            row = cursor.fetchone()
            user = dict(row) if row else None

            if user:
                if not user.get("picture"):
                    user["picture"] = "/static/blank_user.png"
                # Update last_seen to now (ISO format)
                current_timestamp = helper.epoch_to_iso(int(time.time()))
                user["last_seen"] = current_timestamp
                connection.execute("UPDATE users SET last_seen = ? WHERE email = ?;",
                                   (current_timestamp, user["email"]))
                connection.commit()

        else:
            rows = cursor.fetchall()
            user = []
            for r in rows:
                row_dict = dict(r)
                if not row_dict.get("picture"):
                    row_dict["picture"] = "/static/blank_user.png"

                if row_dict.get("last_seen"):

                    try:
                        epoch = helper.iso_to_epoch(row_dict["last_seen"])
                        seconds_ago = int(time.time()) - epoch
                        row_dict["last_seen"] = helper.rough_time_ago(seconds_ago)
                    except:
                        row_dict["last_seen"] = "unknown"
                else:
                    row_dict["last_seen"] = "never"

                user.append(row_dict)

    except Exception as exc:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.exception(f"ERROR adding user to db on line {exc_tb.tb_lineno}!\n\t{exc}")
        if "no such table" in f"{exc}":
            # Try to initialize the database
            init_database(connection)
    return user


def update_user(connection, email: str, token: str = None, authorized: int = None, picture: str = None,
                 clock_font: str = None, clock_font_weight: int = None,
                 clock_pattern: str = None, clock_pattern_color: str = None, clock_pattern_bg_color: str = None,
                 clock_pattern_size: int = None, weather_size: int = None):
    user = get_user(connection, email=email)

    if user:
        if token is not None:
            user["token"] = token
        if authorized is not None:
            user["authorized"] = authorized
        if picture is not None:
            user["picture"] = picture
        if clock_font is not None:
            user["clock_font"] = clock_font
        if clock_font_weight is not None:
            user["clock_font_weight"] = clock_font_weight
        if clock_pattern is not None:
            user["clock_pattern"] = clock_pattern
        if clock_pattern_color is not None:
            user["clock_pattern_color"] = clock_pattern_color
        if clock_pattern_bg_color is not None:
            user["clock_pattern_bg_color"] = clock_pattern_bg_color
        if clock_pattern_size is not None:
            user["clock_pattern_size"] = clock_pattern_size
        if weather_size is not None:
            user["weather_size"] = weather_size

        sql = """UPDATE users SET token = ?, authorized = ?, picture = ?, clock_font = ?, clock_font_weight = ?,
                 clock_pattern = ?, clock_pattern_color = ?, clock_pattern_bg_color = ?, clock_pattern_size = ?,
                 weather_size = ? WHERE email = ?;"""
        params = (user["token"], user["authorized"], user["picture"], user["clock_font"], user["clock_font_weight"],
                   user["clock_pattern"], user["clock_pattern_color"], user["clock_pattern_bg_color"],
                   user["clock_pattern_size"], user["weather_size"], email)

        try:
            connection.execute(sql, params)
            connection.commit()
        except Exception as exc:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            logger.exception(f"ERROR adding user to db on line {exc_tb.tb_lineno}!\n\t{exc}")


def set_weather_location(connection, email: str, lat, lon, city=None):
    """Separate from update_user because lat/lon/city legitimately need to be set to NULL (cleared)."""
    sql = "UPDATE users SET weather_lat = ?, weather_lon = ?, weather_city = ? WHERE email = ?;"

    try:
        connection.execute(sql, (lat, lon, city, email))
        connection.commit()
    except Exception as exc:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        logger.exception(f"ERROR updating weather location on line {exc_tb.tb_lineno}!\n\t{exc}")


def setup_initial_db():
    os.makedirs(temp_dir, exist_ok=True)

    # Always run this, so schema changes (e.g. new columns) reach already-deployed databases too.
    connection = open_db(persist_db)
    init_database(connection)
    close_db(connection)

    if os.path.isfile(temp_db):
        # The shared-memory copy may already exist from before this restart, so migrate it too.
        connection = open_db(temp_db)
        init_database(connection)
        close_db(connection)
    else:
        shutil.copy2(persist_db, temp_db)

def sync_temp_db_to_disk(connection=None):
    if connection:
        close_db(connection)

    # atomic replace. Safer in case of power failure mid copying
    tmp_backup = persist_db + ".tmp"
    shutil.copy2(temp_db, tmp_backup)
    os.replace(tmp_backup, persist_db)


if __name__ == "__main__":
    setup_initial_db()
