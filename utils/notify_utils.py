"""
Sharing utilities:
 - send_report_email(): sends the report file as an email attachment via SMTP.
 - build_whatsapp_link(): builds a wa.me deep link with a pre-filled message.
   (WhatsApp does not allow attaching files through a plain link; the user is
   guided to attach the already-downloaded report inside the opened chat.)
"""
import os
import smtplib
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

from config import Config


def send_report_email(to_email, subject, body_html, attachment_path):
    if not Config.SMTP_USERNAME or not Config.SMTP_PASSWORD:
        raise RuntimeError(
            "Email is not configured. Set SMTP_USERNAME and SMTP_PASSWORD in .env"
        )

    msg = MIMEMultipart()
    msg["From"] = f"{Config.SMTP_FROM_NAME} <{Config.SMTP_USERNAME}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html"))

    with open(attachment_path, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f'attachment; filename="{os.path.basename(attachment_path)}"',
    )
    msg.attach(part)

    with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
        server.starttls()
        server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
        server.sendmail(Config.SMTP_USERNAME, to_email, msg.as_string())


def build_whatsapp_link(phone_number, message):
    """
    phone_number: digits only, with country code, e.g. '919876543210'
    Returns a wa.me link that opens WhatsApp Web / App with the chat + message
    pre-filled. The report file must be attached manually by the user because
    WhatsApp does not support file attachments via URL for security reasons.
    """
    clean_number = "".join(ch for ch in phone_number if ch.isdigit())
    encoded_message = urllib.parse.quote(message)
    if clean_number:
        return f"https://wa.me/{clean_number}?text={encoded_message}"
    return f"https://wa.me/?text={encoded_message}"
