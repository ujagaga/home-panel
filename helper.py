import string
import random
import hashlib
import settings
from datetime import datetime, timezone
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


def generate_token():
    return ''.join(random.choices(string.ascii_letters, k=32))


def email_to_key(email: str) -> str:
    """A short, easy-to-type, non-secret identifier derived from an email address."""
    digest = hashlib.sha256(email.encode()).hexdigest()
    return str(int(digest, 16) % 1_000_000).zfill(6)


def iso_to_epoch(iso_str: str) -> int:
    dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
    return int(dt.timestamp())


def epoch_to_iso(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def rough_time_ago(seconds_ago: int) -> str:
    minutes = seconds_ago // 60
    hours = minutes // 60
    days = hours // 24

    if hours < 24:
        return "today"
    elif days == 1:
        return "yesterday"
    elif days < 7:
        return f"{days} days ago"
    elif days < 30:
        weeks = days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif days < 365:
        months = days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    else:
        return "more than a year ago"


'''
Sends an email using configured credentials.
'''
def send_email(recipient, subject, body):
    msg = MIMEMultipart()
    msg['From'] = settings.SMTP_USER
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        logger.info(f"Sending email to: {recipient}")
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.ehlo()
            # Add if needed:
            # server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.sendmail(settings.SMTP_USER, recipient, msg.as_string())
            logger.info("Sending email done")

    except Exception as e:
        logger.exception(f"Error sending email: {e}")
